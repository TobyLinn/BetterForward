"""Captcha functionality for BetterForward."""

import json
import random
import time

from diskcache import Cache
from telebot import types

from src.config import _


class CaptchaManager:
    """Manages captcha generation and verification."""

    def __init__(self, bot, cache: Cache):
        self.bot = bot
        self.cache = cache
        # 验证码配置
        self.max_attempts = 5  # 最大尝试次数
        self.captcha_timeout = 180  # 验证码超时时间（秒）
        self.lockout_duration = 300  # 失败后锁定时间（秒）
        self.lockout_after_attempts = 3  # 失败多少次后锁定

    def _get_failure_count(self, user_id: int) -> int:
        """获取用户失败次数."""
        return self.cache.get(f"captcha_failures_{user_id}", 0)

    def _increment_failure_count(self, user_id: int):
        """增加失败次数."""
        count = self._get_failure_count(user_id) + 1
        self.cache.set(f"captcha_failures_{user_id}", count, 3600)  # 1小时过期
        
        # 如果失败次数达到锁定阈值，锁定用户（存储锁定时间戳）
        if count >= self.lockout_after_attempts:
            lock_until = time.time() + self.lockout_duration
            self.cache.set(f"captcha_locked_{user_id}", lock_until, self.lockout_duration)

    def _reset_failure_count(self, user_id: int):
        """重置失败次数."""
        self.cache.delete(f"captcha_failures_{user_id}")
        self.cache.delete(f"captcha_locked_{user_id}")

    def _is_user_locked(self, user_id: int) -> bool:
        """检查用户是否被锁定."""
        lock_until = self.cache.get(f"captcha_locked_{user_id}")
        if lock_until is None:
            return False
        # 检查是否还在锁定期内
        if time.time() < lock_until:
            return True
        # 锁定已过期，清除
        self.cache.delete(f"captcha_locked_{user_id}")
        return False
    
    def _get_lock_remaining_time(self, user_id: int) -> int:
        """获取锁定剩余时间（秒）."""
        lock_until = self.cache.get(f"captcha_locked_{user_id}")
        if lock_until is None:
            return 0
        remaining = int(lock_until - time.time())
        return max(0, remaining)

    def _get_remaining_attempts(self, user_id: int) -> int:
        """获取剩余尝试次数."""
        failures = self._get_failure_count(user_id)
        return max(0, self.max_attempts - failures)

    def _generate_math_captcha(self, user_id: int, difficulty: str = "medium") -> tuple[str, int]:
        """生成数学验证码.
        
        Args:
            user_id: 用户ID
            difficulty: 难度级别 (easy, medium, hard)
            
        Returns:
            (问题字符串, 答案)
        """
        failures = self._get_failure_count(user_id)
        
        # 根据失败次数调整难度
        if failures >= 3:
            difficulty = "hard"
        elif failures >= 1:
            difficulty = "medium"
        
        match difficulty:
            case "easy":
                # 简单：10以内的加法
                num1 = random.randint(1, 10)
                num2 = random.randint(1, 10)
                answer = num1 + num2
                question = f"{num1} + {num2} = ?"
            case "medium":
                # 中等：20以内的加减法
                operation = random.choice(["+", "-"])
                if operation == "+":
                    num1 = random.randint(5, 20)
                    num2 = random.randint(5, 20)
                    answer = num1 + num2
                else:
                    num1 = random.randint(10, 30)
                    num2 = random.randint(1, num1)
                    answer = num1 - num2
                question = f"{num1} {operation} {num2} = ?"
            case "hard":
                # 困难：混合运算或乘法
                operation_type = random.choice(["add_sub", "multiply", "complex"])
                if operation_type == "multiply":
                    num1 = random.randint(2, 9)
                    num2 = random.randint(2, 9)
                    answer = num1 * num2
                    question = f"{num1} × {num2} = ?"
                elif operation_type == "complex":
                    # 两步运算：如 (a + b) - c
                    a = random.randint(5, 15)
                    b = random.randint(5, 15)
                    c = random.randint(1, min(a + b - 1, 10))
                    answer = (a + b) - c
                    question = f"({a} + {b}) - {c} = ?"
                else:
                    # 大数加减
                    num1 = random.randint(20, 50)
                    num2 = random.randint(10, num1)
                    answer = num1 - num2
                    question = f"{num1} - {num2} = ?"
            case _:
                # 默认中等难度
                num1 = random.randint(5, 20)
                num2 = random.randint(5, 20)
                answer = num1 + num2
                question = f"{num1} + {num2} = ?"
        
        return question, answer

    def generate_captcha(self, user_id: int, captcha_type: str = "math", db=None):
        """Generate a captcha for the user."""
        # 检查用户是否被锁定
        if self._is_user_locked(user_id):
            lock_seconds = self._get_lock_remaining_time(user_id)
            if lock_seconds > 0:
                return None, _("You have failed too many times. Please try again in {} seconds.").format(lock_seconds)
        
        match captcha_type:
            case "math":
                question, answer = self._generate_math_captcha(user_id)
                # 存储答案和生成时间
                captcha_data = {
                    "answer": answer,
                    "created_at": time.time(),
                    "attempts": 0
                }
                self.cache.set(f"captcha_{user_id}", captcha_data, self.captcha_timeout)
                return question, None
            case "button":
                # 增强按钮验证：添加时间戳和随机token
                import hashlib
                timestamp = int(time.time())
                token = hashlib.sha256(f"{user_id}_{timestamp}_{random.randint(1000, 9999)}".encode()).hexdigest()[:16]
                
                button_data = {
                    "user_id": user_id,
                    "timestamp": timestamp,
                    "token": token,
                    "created_at": time.time()
                }
                self.cache.set(f"button_captcha_{user_id}", button_data, self.captcha_timeout)
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    _("Click to verify"),
                    callback_data=json.dumps({"action": "verify_button", "user_id": user_id, "token": token})
                ))
                self.bot.send_message(user_id, _("Please click the button to verify."),
                                      reply_markup=markup)
                return None, None
            case _:
                raise ValueError(_("Invalid captcha setting"))

    def verify_captcha(self, user_id: int, answer: str, db=None) -> tuple[bool, str]:
        """Verify a captcha answer.
        
        Returns:
            (是否通过, 错误消息)
        """
        # 检查用户是否被锁定
        if self._is_user_locked(user_id):
            lock_seconds = self._get_lock_remaining_time(user_id)
            if lock_seconds > 0:
                return False, _("You are temporarily locked. Please try again in {} seconds.").format(lock_seconds)
        
        captcha_data = self.cache.get(f"captcha_{user_id}")
        if captcha_data is None:
            return False, _("Captcha expired. Please request a new one.")
        
        # 检查是否超时
        if time.time() - captcha_data.get("created_at", 0) > self.captcha_timeout:
            self.cache.delete(f"captcha_{user_id}")
            return False, _("Captcha expired. Please request a new one.")
        
        # 检查尝试次数
        attempts = captcha_data.get("attempts", 0)
        if attempts >= self.max_attempts:
            self._increment_failure_count(user_id)
            self.cache.delete(f"captcha_{user_id}")
            return False, _("Too many failed attempts. Please request a new captcha.")
        
        # 验证答案
        correct_answer = captcha_data.get("answer")
        if str(answer).strip() == str(correct_answer):
            # 验证成功，重置失败次数
            self._reset_failure_count(user_id)
            self.cache.delete(f"captcha_{user_id}")
            
            # 记录验证历史
            if db:
                self._log_verification(user_id, db, success=True)
            
            return True, _("Verification successful!")
        else:
            # 验证失败
            attempts += 1
            captcha_data["attempts"] = attempts
            self.cache.set(f"captcha_{user_id}", captcha_data, self.captcha_timeout)
            self._increment_failure_count(user_id)
            
            remaining = self._get_remaining_attempts(user_id)
            if remaining <= 0:
                self.cache.delete(f"captcha_{user_id}")
                return False, _("Too many failed attempts. Please request a new captcha.")
            
            # 记录验证历史
            if db:
                self._log_verification(user_id, db, success=False)
            
            return False, _("Incorrect answer. {} attempts remaining.").format(remaining)

    def verify_button_captcha(self, user_id: int, token: str, db=None) -> tuple[bool, str]:
        """Verify button captcha.
        
        Returns:
            (是否通过, 错误消息)
        """
        button_data = self.cache.get(f"button_captcha_{user_id}")
        if button_data is None:
            return False, _("Verification expired. Please request a new one.")
        
        # 检查时间戳（防止重放攻击）
        if time.time() - button_data.get("created_at", 0) > self.captcha_timeout:
            self.cache.delete(f"button_captcha_{user_id}")
            return False, _("Verification expired. Please request a new one.")
        
        # 验证token
        if button_data.get("token") != token or button_data.get("user_id") != user_id:
            self._increment_failure_count(user_id)
            if db:
                self._log_verification(user_id, db, success=False)
            return False, _("Invalid verification token.")
        
        # 验证成功
        self._reset_failure_count(user_id)
        self.cache.delete(f"button_captcha_{user_id}")
        
        if db:
            self._log_verification(user_id, db, success=True)
        
        return True, _("Verification successful!")

    def _log_verification(self, user_id: int, db, success: bool):
        """记录验证历史."""
        try:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO captcha_history (user_id, success, timestamp) VALUES (?, ?, ?)",
                (user_id, 1 if success else 0, int(time.time()))
            )
            db.commit()
        except Exception:
            # 如果表不存在，忽略错误
            pass

    def is_user_verified(self, user_id: int, db) -> bool:
        """Check if a user is verified."""
        verified = self.cache.get(f"verified_{user_id}")
        if verified is None:
            cursor = db.cursor()
            result = cursor.execute("SELECT 1 FROM verified_users WHERE user_id = ? LIMIT 1",
                                    (user_id,))
            verified = result.fetchone() is not None
            self.cache.set(f"verified_{user_id}", verified, 1800)
        return verified

    def set_user_verified(self, user_id: int, db):
        """Mark a user as verified."""
        cursor = db.cursor()
        cursor.execute("INSERT OR REPLACE INTO verified_users (user_id) VALUES (?)", (user_id,))
        db.commit()
        self.cache.set(f"verified_{user_id}", True, 1800)

    def remove_user_verification(self, user_id: int, db):
        """Remove user verification status."""
        cursor = db.cursor()
        cursor.execute("DELETE FROM verified_users WHERE user_id = ?", (user_id,))
        db.commit()
        self.cache.delete(f"verified_{user_id}")
        # 同时清除失败记录
        self._reset_failure_count(user_id)

    def get_user_verification_stats(self, user_id: int, db) -> dict:
        """获取用户验证统计信息."""
        try:
            cursor = db.cursor()
            # 获取最近24小时的验证记录
            cursor.execute(
                """SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                   FROM captcha_history 
                   WHERE user_id = ? AND timestamp > ?""",
                (user_id, int(time.time()) - 86400)
            )
            result = cursor.fetchone()
            if result:
                return {
                    "total": result[0] or 0,
                    "successful": result[1] or 0,
                    "failed": result[2] or 0
                }
        except Exception:
            pass
        return {"total": 0, "successful": 0, "failed": 0}
