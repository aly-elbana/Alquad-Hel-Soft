import serial
import pyautogui
import time

try:
    # نفس البورت والسرعة بتوعك
    arduino = serial.Serial("COM5", 115200, timeout=0.1)
    time.sleep(2)
    print("تم الاتصال! حط السنسور على الترابيزة واثبت...")
except Exception as e:
    print(f"مشكلة اتصال: {e}")
    exit()

# ================= إعدادات الفلترة (نفس أرقامك) =================
DEADZONE = 150

# ================= متغيرات المعايرة =================
offset_x = 0
offset_y = 0
calibration_samples = 0
is_calibrated = False

# ================= إعدادات السرعة =================
sensitivity_divider = 200
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# متغير لمنع تكرار الكليك
btn_pressed = False

print("\n!!! جاري حساب الصفر... لا تلمس السنسور !!!\n")

while True:
    try:
        if arduino.in_waiting > 0:
            data = arduino.readline().decode("utf-8").strip()

            if "," in data:
                parts = data.split(",")
                # عدلنا الشرط لـ 4 عشان نستقبل الزرارين كمان
                if len(parts) == 4:
                    raw_gz = float(parts[0])
                    raw_gy = float(parts[1])
                    btn_d3 = int(parts[2])  # زرار D3
                    btn_d5 = int(parts[3])  # زرار D5

                    # 1. مرحلة المعايرة (زي ما هي)
                    if not is_calibrated:
                        offset_x += raw_gz
                        offset_y += raw_gy
                        calibration_samples += 1

                        if calibration_samples % 50 == 0:
                            print(f"جاري المعايرة... {calibration_samples}/500")

                        if calibration_samples >= 500:
                            offset_x /= 500
                            offset_y /= 500
                            is_calibrated = True
                            print("\n=== تمت المعايرة بنجاح! البس السنسور دلوقتي ===\n")
                        continue

                    # 2. تطبيق المعايرة
                    corrected_gz = raw_gz - offset_x
                    corrected_gy = raw_gy - offset_y

                    # 3. الفلتر القوي (Deadzone) - زي كودك بالظبط
                    if abs(corrected_gz) < DEADZONE:
                        corrected_gz = 0
                    if abs(corrected_gy) < DEADZONE:
                        corrected_gy = 0

                    # 4. معادلة الحركة (زي كودك بالظبط)
                    move_x = corrected_gz / sensitivity_divider
                    move_y = -1 * (corrected_gy / sensitivity_divider)

                    # لو فيه حركة، نفذها
                    if corrected_gz != 0 or corrected_gy != 0:
                        pyautogui.moveRel(move_x, move_y)

                    # ================= 5. منطق الزراير (الجديد) =================
                    # لو أي زرار مضغوط
                    if btn_d3 == 1 or btn_d5 == 1:
                        if not btn_pressed:  # عشان ينفذ الأمر مرة واحدة بس
                            if btn_d3 == 1:
                                pyautogui.click(button="left")
                                print("Left Click (D3)")
                            elif btn_d5 == 1:
                                pyautogui.click(button="right")
                                print("Right Click (D5)")

                            btn_pressed = True  # اقفل البوابة
                    else:
                        btn_pressed = False  # افتح البوابة لما يشيل ايده

    except Exception as e:
        print(f"Error: {e}")
        break
