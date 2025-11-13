"""Captcha functionality for BetterForward."""

import io
import json
import random
import sqlite3
import time

from diskcache import Cache
from PIL import Image, ImageDraw, ImageFont
from telebot import types

from src.config import _, logger


class CaptchaManager:
    """Manages captcha generation and verification."""

    # 验证码配置常量
    DEFAULT_MAX_ATTEMPTS = 3  # 最大尝试次数（降低以提高安全性）
    DEFAULT_CAPTCHA_TIMEOUT = 120  # 验证码超时时间（秒）
    DEFAULT_LOCKOUT_DURATION = 600  # 失败后锁定时间（秒）- 10分钟
    DEFAULT_LOCKOUT_AFTER_ATTEMPTS = 2  # 失败多少次后锁定（降低阈值）
    DEFAULT_MIN_ANSWER_TIME = 3  # 最小回答时间（秒）- 防止自动化
    DEFAULT_MAX_ANSWER_TIME = 60  # 最大回答时间（秒）
    
    # 图片验证码配置常量
    IMAGE_PADDING = 60  # 左右边距（像素）
    IMAGE_CHAR_SPACING = 100  # 每个字符的宽度（像素）
    IMAGE_HEIGHT = 180  # 图片高度（像素）
    IMAGE_FONT_SIZE = 80  # 字体大小（像素）
    IMAGE_CHAR_WIDTH = 95  # 字符临时图片宽度（像素）
    IMAGE_CHAR_HEIGHT = 115  # 字符临时图片高度（像素）
    IMAGE_MAX_OFFSET = 10  # 最大位置偏移（像素）
    IMAGE_INTERFERENCE_LINES = 5  # 干扰线数量
    IMAGE_INTERFERENCE_DOTS = 50  # 干扰点数量
    IMAGE_ROTATION_ANGLE = 15  # 字符旋转角度范围（度）

    def __init__(self, bot, cache: Cache):
        self.bot = bot
        self.cache = cache
        # 验证码配置（可以从数据库或环境变量读取）
        self.max_attempts = self.DEFAULT_MAX_ATTEMPTS
        self.captcha_timeout = self.DEFAULT_CAPTCHA_TIMEOUT
        self.lockout_duration = self.DEFAULT_LOCKOUT_DURATION
        self.lockout_after_attempts = self.DEFAULT_LOCKOUT_AFTER_ATTEMPTS
        self.min_answer_time = self.DEFAULT_MIN_ANSWER_TIME
        self.max_answer_time = self.DEFAULT_MAX_ANSWER_TIME
        
        # 字体缓存（避免重复加载）
        self._cached_font = None
        self._cached_font_path = None

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
    
    def _get_font(self, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """获取字体对象，使用缓存避免重复加载.
        
        Args:
            font_size: 字体大小
            
        Returns:
            PIL ImageFont 对象
        """
        # 如果字体大小相同且已缓存，直接返回
        if self._cached_font and self._cached_font_path:
            try:
                # 尝试使用缓存的字体路径
                return ImageFont.truetype(self._cached_font_path, font_size)
            except (OSError, IOError) as e:
                logger.debug(f"Cached font path invalid, reloading: {e}")
                self._cached_font = None
                self._cached_font_path = None
        
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
        
        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                # 缓存成功的字体路径
                self._cached_font_path = font_path
                logger.debug(f"Successfully loaded font from {font_path}")
                break
            except (OSError, IOError) as e:
                logger.debug(f"Failed to load font from {font_path}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error loading font from {font_path}: {e}")
                continue
        
        # 如果所有路径都失败，使用默认字体
        if font is None:
            logger.warning("All font paths failed, using default font")
            font = ImageFont.load_default()
        
        return font

    def _generate_image_captcha(self, user_id: int) -> tuple[io.BytesIO, str]:
        """生成图片验证码（英文+数字，区分大小写）.
        
        Args:
            user_id: 用户ID
            
        Returns:
            (图片字节流, 答案字符串)
            
        Raises:
            Exception: 如果图片生成失败
        """
        try:
            # 生成4-5位英文+数字验证码（区分大小写）
            # 包含：大写字母 A-Z, 小写字母 a-z, 数字 0-9
            chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            code_length = random.choice([4, 5])  # 随机4或5位
            code = ''.join([random.choice(chars) for _ in range(code_length)])
            
            logger.debug(f"Generating image captcha for user {user_id}, code length: {code_length}")
            
            # 增加图片尺寸和边距，确保字符旋转后不会超出边界
            padding = self.IMAGE_PADDING
            char_spacing = self.IMAGE_CHAR_SPACING
            width = padding * 2 + code_length * char_spacing
            height = self.IMAGE_HEIGHT
            
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # 尝试加载字体，如果失败则使用默认字体
            font = self._get_font(self.IMAGE_FONT_SIZE)
            
            # 绘制干扰线（在安全区域内）
            safe_margin = 10
            for _ in range(self.IMAGE_INTERFERENCE_LINES):
                x1 = random.randint(safe_margin, width - safe_margin)
                y1 = random.randint(safe_margin, height - safe_margin)
                x2 = random.randint(safe_margin, width - safe_margin)
                y2 = random.randint(safe_margin, height - safe_margin)
                draw.line([(x1, y1), (x2, y2)], fill=(random.randint(150, 255), random.randint(150, 255), random.randint(150, 255)), width=2)
            
            # 绘制干扰点
            for _ in range(self.IMAGE_INTERFERENCE_DOTS):
                x = random.randint(safe_margin, width - safe_margin)
                y = random.randint(safe_margin, height - safe_margin)
                draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            
            # 绘制验证码文字（每个字符位置略有偏移，增加难度）
            char_img_width = self.IMAGE_CHAR_WIDTH
            char_img_height = self.IMAGE_CHAR_HEIGHT
            safe_margin = 15
            
            for i, char in enumerate(code):
                # 计算字符中心位置（在安全区域内）
                char_center_x = padding + i * char_spacing + char_spacing // 2
                char_center_y = height // 2
                
                # 随机位置偏移（限制在安全范围内）
                x_offset = random.randint(-self.IMAGE_MAX_OFFSET, self.IMAGE_MAX_OFFSET)
                y_offset = random.randint(-self.IMAGE_MAX_OFFSET, self.IMAGE_MAX_OFFSET)
                
                # 计算粘贴位置（确保不超出边界）
                x = char_center_x - char_img_width // 2 + x_offset
                y = char_center_y - char_img_height // 2 + y_offset
                
                # 确保位置在安全范围内
                x = max(safe_margin, min(x, width - char_img_width - safe_margin))
                y = max(safe_margin, min(y, height - char_img_height - safe_margin))
                
                # 随机颜色（深色，确保在白色背景上可见）
                color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
                
                # 随机旋转角度
                angle = random.randint(-self.IMAGE_ROTATION_ANGLE, self.IMAGE_ROTATION_ANGLE)
                
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
            
            logger.debug(f"Image captcha generated successfully for user {user_id}")
            return img_byte_arr, code
        except Exception as e:
            logger.error(f"Failed to generate image captcha for user {user_id}: {e}")
            raise

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
                try:
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
                    
                    logger.info(f"Image captcha generated and sent to user {user_id}")
                    return None, None
                except Exception as e:
                    logger.error(f"Failed to generate image captcha for user {user_id}: {e}")
                    return None, _("Failed to generate captcha. Please try again later.")
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
        
        Args:
            user_id: 用户ID
            answer: 用户提交的答案
            db: 数据库连接（可选）
        
        Returns:
            (是否通过, 错误消息)
        """
        try:
            # 检查用户是否被锁定
            if self._is_user_locked(user_id):
                lock_seconds = self._get_lock_remaining_time(user_id)
                if lock_seconds > 0:
                    logger.info(f"User {user_id} attempted captcha while locked, remaining: {lock_seconds}s")
                    return False, _("You are temporarily locked. Please try again in {} seconds.").format(lock_seconds)
            
            captcha_data = self.cache.get(f"captcha_{user_id}")
            if captcha_data is None:
                logger.debug(f"User {user_id} attempted captcha but no captcha found")
                return False, _("Captcha expired. Please request a new one.")
            
            created_at = captcha_data.get("created_at", 0)
            elapsed_time = time.time() - created_at
            
            # 检查是否超时
            if elapsed_time > self.captcha_timeout:
                self.cache.delete(f"captcha_{user_id}")
                logger.debug(f"Captcha expired for user {user_id}, elapsed: {elapsed_time}s")
                return False, _("Captcha expired. Please request a new one.")
            
            # 反自动化检测：检查回答时间
            if elapsed_time < self.min_answer_time:
                # 回答太快，可能是自动化脚本
                attempts = captcha_data.get("attempts", 0) + 1
                captcha_data["attempts"] = attempts
                self.cache.set(f"captcha_{user_id}", captcha_data, self.captcha_timeout)
                self._increment_failure_count(user_id)
                logger.warning(f"User {user_id} answered too quickly: {elapsed_time:.2f}s < {self.min_answer_time}s")
                if db:
                    self._log_verification(user_id, db, success=False)
                return False, _("Answer submitted too quickly. Please wait at least {} seconds and try again.").format(self.min_answer_time)
            
            # 检查是否超过最大回答时间
            if elapsed_time > self.max_answer_time:
                self.cache.delete(f"captcha_{user_id}")
                logger.debug(f"User {user_id} answered too slowly: {elapsed_time:.2f}s > {self.max_answer_time}s")
                return False, _("Answer submitted too slowly. Please request a new captcha.")
            
            # 检查尝试次数
            attempts = captcha_data.get("attempts", 0)
            if attempts >= self.max_attempts:
                self._increment_failure_count(user_id)
                self.cache.delete(f"captcha_{user_id}")
                logger.warning(f"User {user_id} exceeded max attempts: {attempts}")
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
                    
                    logger.info(f"User {user_id} passed image captcha verification")
                    return True, _("Verification successful!")
                else:
                    # 验证失败
                    attempts += 1
                    captcha_data["attempts"] = attempts
                    self._increment_failure_count(user_id)
                    
                    remaining = self._get_remaining_attempts(user_id)
                    logger.info(f"User {user_id} failed image captcha, attempts: {attempts}, remaining: {remaining}")
                    
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
                        
                        logger.info(f"User {user_id} passed math captcha verification")
                        return True, _("Verification successful!")
                    else:
                        # 验证失败
                        attempts += 1
                        captcha_data["attempts"] = attempts
                        self._increment_failure_count(user_id)
                        
                        remaining = self._get_remaining_attempts(user_id)
                        logger.info(f"User {user_id} failed math captcha, attempts: {attempts}, remaining: {remaining}")
                        
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
                    logger.warning(f"User {user_id} provided invalid answer format for math captcha, remaining: {remaining}")
                    
                    if remaining <= 0:
                        # 尝试次数用完，删除验证码
                        self.cache.delete(f"captcha_{user_id}")
                        return False, _("Invalid answer format. Please enter a number.")
                    
                    # 删除当前验证码，强制重新生成
                    self.cache.delete(f"captcha_{user_id}")
                    
                    if db:
                        self._log_verification(user_id, db, success=False)
                    
                    return False, _("Invalid answer format. Please enter a number. {} attempts remaining. A new captcha will be generated.").format(remaining)
        except Exception as e:
            logger.error(f"Unexpected error verifying captcha for user {user_id}: {e}")
            return False, _("An error occurred during verification. Please try again.")

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
        """记录验证历史.
        
        Args:
            user_id: 用户ID
            db: 数据库连接
            success: 是否验证成功
        """
        try:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO captcha_history (user_id, success, timestamp) VALUES (?, ?, ?)",
                (user_id, 1 if success else 0, int(time.time()))
            )
            db.commit()
            logger.debug(f"Logged verification for user {user_id}: success={success}")
        except sqlite3.OperationalError as e:
            # 表不存在或其他数据库操作错误
            logger.debug(f"Database operation failed (table may not exist): {e}")
        except Exception as e:
            logger.error(f"Unexpected error logging verification for user {user_id}: {e}")

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

