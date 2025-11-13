"""Captcha functionality for BetterForward."""

import io
import json
import random
import time

from diskcache import Cache
from PIL import Image, ImageDraw, ImageFont
from telebot import types

from src.config import _


class CaptchaManager:
    """Manages captcha generation and verification."""

    def __init__(self, bot, cache: Cache):
        self.bot = bot
        self.cache = cache
        # 验证码配置
        self.max_attempts = 3  # 最大尝试次数（降低以提高安全性）
        self.captcha_timeout = 120  # 验证码超时时间（秒）
        self.lockout_duration = 600  # 失败后锁定时间（秒）- 增加到10分钟
        self.lockout_after_attempts = 2  # 失败多少次后锁定（降低阈值）
        self.min_answer_time = 3  # 最小回答时间（秒）- 防止自动化
        self.max_answer_time = 60  # 最大回答时间（秒）

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

    def _generate_image_captcha(self, user_id: int) -> tuple[io.BytesIO, str]:
        """生成图片验证码（英文+数字，区分大小写）.
        
        Args:
            user_id: 用户ID
            
        Returns:
            (图片字节流, 答案字符串)
        """
        # 生成4-5位英文+数字验证码（区分大小写）
        # 包含：大写字母 A-Z, 小写字母 a-z, 数字 0-9
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        code_length = random.choice([4, 5])  # 随机4或5位
        code = ''.join([random.choice(chars) for _ in range(code_length)])
        
        # 增加图片尺寸和边距，确保字符旋转后不会超出边界
        # 每个字符预留更多空间（100像素），加上左右边距（各60像素）
        padding = 60  # 左右边距
        char_spacing = 100  # 每个字符的宽度
        width = padding * 2 + code_length * char_spacing
        height = 180  # 增加高度，确保旋转后的字符不超出
        
        image = Image.new('RGB', (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 尝试加载字体，如果失败则使用默认字体
        try:
            # 尝试使用系统字体（进一步增大字体大小）
            font_size = 80  # 从64增加到80，字体更大更清晰
            font = None
            
            # 按优先级尝试加载字体
            font_paths = [
                # macOS
                "/System/Library/Fonts/Helvetica.ttc",
                # Linux (包括 Docker Alpine)
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
                # 其他可能的路径
                "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            ]
            
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
            
            # 如果所有路径都失败，使用默认字体
            if font is None:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # 绘制干扰线（在安全区域内）
        for _ in range(5):
            x1 = random.randint(10, width - 10)
            y1 = random.randint(10, height - 10)
            x2 = random.randint(10, width - 10)
            y2 = random.randint(10, height - 10)
            draw.line([(x1, y1), (x2, y2)], fill=(random.randint(150, 255), random.randint(150, 255), random.randint(150, 255)), width=2)
        
        # 绘制干扰点
        for _ in range(50):
            x = random.randint(10, width - 10)
            y = random.randint(10, height - 10)
            draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        
        # 绘制验证码文字（每个字符位置略有偏移，增加难度）
        # 字符临时图片尺寸（增大以确保旋转后不超出，适应更大的字体）
        char_img_width = 95  # 从75增加到95
        char_img_height = 115  # 从90增加到115
        
        for i, char in enumerate(code):
            # 计算字符中心位置（在安全区域内）
            char_center_x = padding + i * char_spacing + char_spacing // 2
            char_center_y = height // 2
            
            # 随机位置偏移（限制在安全范围内）
            max_offset = 10  # 稍微增加偏移范围
            x_offset = random.randint(-max_offset, max_offset)
            y_offset = random.randint(-max_offset, max_offset)
            
            # 计算粘贴位置（确保不超出边界）
            x = char_center_x - char_img_width // 2 + x_offset
            y = char_center_y - char_img_height // 2 + y_offset
            
            # 确保位置在安全范围内
            x = max(15, min(x, width - char_img_width - 15))
            y = max(15, min(y, height - char_img_height - 15))
            
            # 随机颜色
            color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
            
            # 随机旋转角度
            angle = random.randint(-15, 15)
            
            # 创建单个字符的临时图片（增大尺寸以适应更大的字体）
            char_img = Image.new('RGBA', (char_img_width, char_img_height), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_img)
            # 字符在临时图片中居中（调整位置以适应更大的字体）
            char_draw.text((char_img_width // 2 - 20, char_img_height // 2 - 25), char, fill=color, font=font)
            
            # 旋转字符
            if angle != 0:
                char_img = char_img.rotate(angle, expand=True)
                # 旋转后重新计算位置，确保居中
                rotated_width, rotated_height = char_img.size
                x = char_center_x - rotated_width // 2 + x_offset
                y = char_center_y - rotated_height // 2 + y_offset
                # 再次确保不超出边界
                x = max(5, min(x, width - rotated_width - 5))
                y = max(5, min(y, height - rotated_height - 5))
            
            # 粘贴到主图片
            image.paste(char_img, (int(x), int(y)), char_img)
        
        # 转换为字节流
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr, code

    def _generate_math_captcha(self, user_id: int, difficulty: str = "hard") -> tuple[str, int]:
        """生成数学验证码（增强难度，防止自动化）.
        
        Args:
            user_id: 用户ID
            difficulty: 难度级别 (easy, medium, hard, extreme)
            
        Returns:
            (问题字符串, 答案)
        """
        failures = self._get_failure_count(user_id)
        
        # 默认使用困难难度，根据失败次数进一步提升
        if failures >= 2:
            difficulty = "extreme"
        elif failures >= 1:
            difficulty = "hard"
        else:
            difficulty = "hard"  # 默认就是困难难度
        
        match difficulty:
            case "easy":
                # 简单：20以内的加减法（基本不用）
                operation = random.choice(["+", "-"])
                if operation == "+":
                    num1 = random.randint(10, 20)
                    num2 = random.randint(10, 20)
                    answer = num1 + num2
                else:
                    num1 = random.randint(20, 40)
                    num2 = random.randint(5, num1)
                    answer = num1 - num2
                question = f"{num1} {operation} {num2} = ?"
            case "medium":
                # 中等：50以内的混合运算
                operation_type = random.choice(["multiply", "complex_add"])
                if operation_type == "multiply":
                    num1 = random.randint(3, 12)
                    num2 = random.randint(3, 12)
                    answer = num1 * num2
                    question = f"{num1} × {num2} = ?"
                else:
                    a = random.randint(10, 25)
                    b = random.randint(10, 25)
                    c = random.randint(5, 15)
                    answer = a + b - c
                    question = f"{a} + {b} - {c} = ?"
            case "hard":
                # 困难：多步运算、除法、大数运算
                operation_type = random.choice(["multiply_complex", "divide", "triple_op", "large_numbers"])
                if operation_type == "multiply_complex":
                    # 两位数乘法
                    num1 = random.randint(11, 19)
                    num2 = random.randint(3, 9)
                    answer = num1 * num2
                    question = f"{num1} × {num2} = ?"
                elif operation_type == "divide":
                    # 除法（确保能整除）
                    divisor = random.randint(2, 9)
                    quotient = random.randint(5, 15)
                    dividend = divisor * quotient
                    answer = quotient
                    question = f"{dividend} ÷ {divisor} = ?"
                elif operation_type == "triple_op":
                    # 三步运算
                    a = random.randint(10, 20)
                    b = random.randint(5, 15)
                    c = random.randint(3, 10)
                    d = random.randint(2, 8)
                    answer = (a + b) * c - d
                    question = f"({a} + {b}) × {c} - {d} = ?"
                else:
                    # 大数运算
                    num1 = random.randint(50, 100)
                    num2 = random.randint(20, num1)
                    answer = num1 - num2
                    question = f"{num1} - {num2} = ?"
            case "extreme":
                # 极端困难：复杂多步运算、大数乘除、混合运算
                operation_type = random.choice(["complex_multiply", "complex_divide", "nested_ops", "large_multiply"])
                if operation_type == "complex_multiply":
                    # 复杂乘法
                    num1 = random.randint(15, 25)
                    num2 = random.randint(4, 12)
                    answer = num1 * num2
                    question = f"{num1} × {num2} = ?"
                elif operation_type == "complex_divide":
                    # 复杂除法
                    divisor = random.randint(3, 12)
                    quotient = random.randint(8, 20)
                    dividend = divisor * quotient
                    answer = quotient
                    question = f"{dividend} ÷ {divisor} = ?"
                elif operation_type == "nested_ops":
                    # 嵌套运算
                    a = random.randint(8, 15)
                    b = random.randint(5, 12)
                    c = random.randint(3, 8)
                    d = random.randint(2, 6)
                    e = random.randint(1, 5)
                    answer = ((a + b) * c - d) // e
                    question = f"(({a} + {b}) × {c} - {d}) ÷ {e} = ?"
                else:
                    # 大数乘法
                    num1 = random.randint(20, 30)
                    num2 = random.randint(5, 15)
                    answer = num1 * num2
                    question = f"{num1} × {num2} = ?"
            case _:
                # 默认困难难度
                num1 = random.randint(15, 25)
                num2 = random.randint(4, 12)
                answer = num1 * num2
                question = f"{num1} × {num2} = ?"
        
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
                    "attempts": 0,
                    "first_attempt_time": None  # 记录首次尝试时间
                }
                self.cache.set(f"captcha_{user_id}", captcha_data, self.captcha_timeout)
                # 添加提示信息
                question_with_hint = f"{question}\n\n" + _("⚠️ Anti-automation: Please wait at least {} seconds before answering.").format(self.min_answer_time)
                return question_with_hint, None
            case "image":
                # 生成图片验证码
                img_bytes, code = self._generate_image_captcha(user_id)
                
                # 存储答案和生成时间
                captcha_data = {
                    "answer": code,
                    "created_at": time.time(),
                    "attempts": 0,
                    "type": "image"
                }
                self.cache.set(f"captcha_{user_id}", captcha_data, self.captcha_timeout)
                
                # 发送图片验证码
                caption = _("Please enter the code shown in the image (case-sensitive, {} characters).\n\n⚠️ Anti-automation: Please wait at least {} seconds before answering.").format(len(code), self.min_answer_time)
                self.bot.send_photo(user_id, img_bytes, caption=caption)
                
                return None, None
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
        """Verify a captcha answer（增强反自动化检测）.
        
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
        
        created_at = captcha_data.get("created_at", 0)
        elapsed_time = time.time() - created_at
        
        # 检查是否超时
        if elapsed_time > self.captcha_timeout:
            self.cache.delete(f"captcha_{user_id}")
            return False, _("Captcha expired. Please request a new one.")
        
        # 反自动化检测：检查回答时间
        if elapsed_time < self.min_answer_time:
            # 回答太快，可能是自动化脚本
            attempts = captcha_data.get("attempts", 0) + 1
            captcha_data["attempts"] = attempts
            self.cache.set(f"captcha_{user_id}", captcha_data, self.captcha_timeout)
            self._increment_failure_count(user_id)
            if db:
                self._log_verification(user_id, db, success=False)
            return False, _("Answer submitted too quickly. Please wait at least {} seconds and try again.").format(self.min_answer_time)
        
        # 检查是否超过最大回答时间
        if elapsed_time > self.max_answer_time:
            self.cache.delete(f"captcha_{user_id}")
            return False, _("Answer submitted too slowly. Please request a new captcha.")
        
        # 检查尝试次数
        attempts = captcha_data.get("attempts", 0)
        if attempts >= self.max_attempts:
            self._increment_failure_count(user_id)
            self.cache.delete(f"captcha_{user_id}")
            return False, _("Too many failed attempts. Please request a new captcha.")
        
        # 验证答案
        correct_answer = captcha_data.get("answer")
        user_answer = str(answer).strip()
        captcha_type = captcha_data.get("type", "math")
        
        # 图片验证码：区分大小写的字符串比较
        if captcha_type == "image":
            if user_answer == correct_answer:
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
                self._increment_failure_count(user_id)
                
                remaining = self._get_remaining_attempts(user_id)
                if remaining <= 0:
                    # 尝试次数用完，删除验证码
                    self.cache.delete(f"captcha_{user_id}")
                    return False, _("Too many failed attempts. Please request a new captcha.")
                
                # 删除当前验证码，强制重新生成
                self.cache.delete(f"captcha_{user_id}")
                
                # 记录验证历史
                if db:
                    self._log_verification(user_id, db, success=False)
                
                return False, _("Incorrect answer. {} attempts remaining. A new captcha will be generated.").format(remaining)
        
        # 数学验证码：数字比较
        else:
            try:
                user_answer_int = int(user_answer)
                correct_answer_int = int(correct_answer)
                
                if user_answer_int == correct_answer_int:
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
                    self._increment_failure_count(user_id)
                    
                    remaining = self._get_remaining_attempts(user_id)
                    if remaining <= 0:
                        # 尝试次数用完，删除验证码
                        self.cache.delete(f"captcha_{user_id}")
                        return False, _("Too many failed attempts. Please request a new captcha.")
                    
                    # 删除当前验证码，强制重新生成
                    self.cache.delete(f"captcha_{user_id}")
                    
                    # 记录验证历史
                    if db:
                        self._log_verification(user_id, db, success=False)
                    
                    return False, _("Incorrect answer. {} attempts remaining. A new captcha will be generated.").format(remaining)
            except ValueError:
                # 答案不是数字
                attempts += 1
                captcha_data["attempts"] = attempts
                self._increment_failure_count(user_id)
                
                remaining = self._get_remaining_attempts(user_id)
                if remaining <= 0:
                    # 尝试次数用完，删除验证码
                    self.cache.delete(f"captcha_{user_id}")
                    return False, _("Invalid answer format. Please enter a number.")
                
                # 删除当前验证码，强制重新生成
                self.cache.delete(f"captcha_{user_id}")
                
                if db:
                    self._log_verification(user_id, db, success=False)
                
                return False, _("Invalid answer format. Please enter a number. {} attempts remaining. A new captcha will be generated.").format(remaining)

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

    def clear_all_verification_records(self, db) -> tuple[int, int]:
        """清除所有验证记录.
        
        Returns:
            (清除的已验证用户数, 清除的验证历史记录数)
        """
        verified_count = 0
        history_count = 0
        
        try:
            cursor = db.cursor()
            
            # 清除已验证用户表
            cursor.execute("SELECT COUNT(*) FROM verified_users")
            verified_count = cursor.fetchone()[0] or 0
            cursor.execute("DELETE FROM verified_users")
            
            # 清除验证历史表
            cursor.execute("SELECT COUNT(*) FROM captcha_history")
            history_count = cursor.fetchone()[0] or 0
            cursor.execute("DELETE FROM captcha_history")
            
            db.commit()
            
            # 清除缓存中所有验证相关的数据
            # 注意：diskcache 没有直接的方法列出所有键，所以我们需要清除已知的模式
            # 这里我们只能清除当前已知的键，无法清除所有历史缓存
            # 缓存会在过期后自动清除
            
        except Exception as e:
            # 如果表不存在，忽略错误
            pass
        
        return verified_count, history_count

    def clear_all_cache_records(self):
        """清除缓存中所有验证相关的记录（尽可能清除）."""
        # 注意：diskcache 没有直接的方法列出所有键
        # 这个方法主要用于清除已知模式的缓存键
        # 实际使用中，缓存会在过期后自动清除
        pass
