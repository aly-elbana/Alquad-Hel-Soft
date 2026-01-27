import serial
import pyautogui
import time
import numpy as np


# ================= كلاس الكالمان فلتر (للنعومة) =================
class KalmanFilter:
    def __init__(self, process_noise=0.1, measurement_noise=5.0, estimated_error=1.0):
        self.q = process_noise
        self.r = measurement_noise
        self.p = estimated_error
        self.x = 0.0

    def update(self, measurement):
        self.p = self.p + self.q
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (measurement - self.x)
        self.p = (1 - k) * self.p
        return self.x


# ================= الإعدادات =================
try:
    # تأكد من رقم الـ COM الجديد
    arduino = serial.Serial("COM9", 115200, timeout=0.01)
    time.sleep(2)
    print("تم الاتصال! النظام جاهز...")
except Exception as e:
    print(f"مشكلة اتصال: {e}")
    exit()

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# الفلاتر
kf_x = KalmanFilter(process_noise=0.1, measurement_noise=5.0)
kf_y = KalmanFilter(process_noise=0.1, measurement_noise=5.0)

# متغيرات المعايرة
offset_x = 0
offset_y = 0
calibration_samples = 0
is_calibrated = False
SPEED_FACTOR = 150
SCROLL_SPEED = 5  # سرعة السكرول (كل ما يقل يبقى أسرع)

# متغيرات الأزرار والمنطق
is_dragging = False  # حالة الإمساك
is_scroll_mode = False  # حالة السكرول
right_btn_timer = 0  # لحساب وقت الضغط
right_btn_down = False  # هل الزرار مضغوط حالياً؟
scroll_btn_state_prev = 0  # عشان التبديل (Toggle)
left_btn_state_prev = 0  # لمنع تكرار الكليك

print("\n!!! اثبت للمعايرة !!!\n")

while True:
    try:
        if arduino.in_waiting > 0:
            line = arduino.readline().decode("utf-8", errors="ignore").strip()

            if "," in line:
                parts = line.split(",")
                # لازم نستقبل 5 قيم دلوقتي
                if len(parts) == 5:
                    raw_gz = float(parts[0])
                    raw_gy = float(parts[1])
                    btn_left = int(parts[2])
                    btn_right = int(parts[3])
                    btn_scroll = int(parts[4])

                    # --- 1. المعايرة ---
                    if not is_calibrated:
                        offset_x += raw_gz
                        offset_y += raw_gy
                        calibration_samples += 1
                        if calibration_samples >= 500:
                            offset_x /= 500
                            offset_y /= 500
                            is_calibrated = True
                            print("\n=== تمت المعايرة! ===")
                            print("- الزرار 1: كليك شمال")
                            print("- الزرار 2: ضغطة سريعة (يمين) / طويلة (Drag)")
                            print("- الزرار 3: تفعيل/إلغاء السكرول")
                        continue

                    # --- 2. معالجة الحركة ---
                    val_x = raw_gz - offset_x
                    val_y = raw_gy - offset_y
                    smooth_x = kf_x.update(val_x)
                    smooth_y = kf_y.update(val_y)

                    # --- 3. تنفيذ الحركة أو السكرول ---
                    if is_scroll_mode:
                        # في وضع السكرول: حركة الراس فوق/تحت تعمل سكرول
                        if abs(smooth_y) > 100:
                            scroll_amount = int(smooth_y / SCROLL_SPEED)
                            pyautogui.scroll(scroll_amount)
                        # (ممكن تضيف سكرول أفقي بحركة الراس يمين/شمال لو حابب)
                    else:
                        # الوضع العادي: تحريك الماوس
                        if abs(smooth_x) > 100:
                            move_x = smooth_x / SPEED_FACTOR
                        else:
                            move_x = 0

                        if abs(smooth_y) > 100:
                            move_y = -1 * (smooth_y / SPEED_FACTOR)
                        else:
                            move_y = 0

                        if move_x != 0 or move_y != 0:
                            pyautogui.moveRel(move_x, move_y)

                    # --- 4. منطق الزرار الأيسر (Left Click) ---
                    if btn_left == 1 and left_btn_state_prev == 0:
                        pyautogui.click()
                    left_btn_state_prev = btn_left

                    # --- 5. منطق الزرار الأيمن (Right Click VS Drag) ---
                    if btn_right == 1:
                        if not right_btn_down:
                            right_btn_timer = time.time()  # ابدأ العد
                            right_btn_down = True
                    else:
                        if right_btn_down:  # لحظة رفع اليد
                            duration = time.time() - right_btn_timer
                            if duration < 0.5:  # لو الضغطة أقل من نص ثانية
                                pyautogui.rightClick()
                                print("Right Click")
                            else:  # لو الضغطة طويلة
                                is_dragging = not is_dragging  # اعكس الحالة
                                if is_dragging:
                                    pyautogui.mouseDown()
                                    print(">>> Drag ON (ماسك الملف) <<<")
                                else:
                                    pyautogui.mouseUp()
                                    print(">>> Drag OFF (سيبت الملف) <<<")
                            right_btn_down = False

                    # --- 6. منطق زرار السكرول (Toggle) ---
                    if btn_scroll == 1 and scroll_btn_state_prev == 0:
                        is_scroll_mode = not is_scroll_mode  # اعكس الحالة
                        if is_scroll_mode:
                            print("--- Scroll Mode ACTIVE (حرك راسك فوق وتحت) ---")
                        else:
                            print("--- Mouse Mode ACTIVE ---")
                    scroll_btn_state_prev = btn_scroll

    except KeyboardInterrupt:
        break
    except Exception as e:
        pass
