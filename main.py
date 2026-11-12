# -*- coding: utf-8 -*-
"""
نقل الملفات محليًا بين جهازين — النسخة المحسّنة
- شريط تقدم + نسبة مئوية + سرعة النقل
- نقل مجلدات كاملة (يضغطها تلقائيًا)
- استقبال عدة ملفات متتالية بدون إعادة تشغيل الخادم
- لا يوجد أي فلترة على أسماء الملفات — كل شيء يُنقل كما هو
"""
import socket
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
import os
import threading
import zipfile
import time

حجم_القطعة = 64 * 1024  # 64KB لسرعة أفضل

# ------------ الحصول على عنوان IP ------------ #
def الحصول_على_عنوان_IP():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except:
        ip = socket.gethostbyname(socket.gethostname())
    return ip

# ------------ أدوات مساعدة ------------ #
def تحديث_الواجهة(نص):
    الحالة.after(0, lambda: الحالة.config(text=نص))

def تحديث_التقدم(قيمة, كامل):
    نسبة = (قيمة / كامل * 100) if كامل else 0
    شريط_التقدم.after(0, lambda: شريط_التقدم.config(value=نسبة))
    نسبة_النقل.after(0, lambda: نسبة_النقل.config(text=f"{نسبة:.1f}%"))
    واجهة.update_idletasks()

def تنسيق_الحجم(بايت):
    for وحدة in ["B", "KB", "MB", "GB"]:
        if بايت < 1024:
            return f"{بايت:.1f} {وحدة}"
        بايت /= 1024
    return f"{بايت:.1f} TB"

# ------------ استقبال الملفات ------------ #
خادم_يعمل = False

def بدء_استقبال():
    global خادم_يعمل
    مجلد_الحفظ = filedialog.askdirectory(title="اختر مكان حفظ الملفات")
    if not مجلد_الحفظ:
        return

    def خادم():
        global خادم_يعمل
        try:
            ip = الحصول_على_عنوان_IP()
            منفذ = 5001
            تحديث_الواجهة(f"🟢 في الانتظار على {ip}:{منفذ}")

            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((ip, منفذ))
            s.listen(5)

            خادم_يعمل = True
            while خادم_يعمل:
                try:
                    s.settimeout(1.0)
                    اتصال, عنوان = s.accept()
                except socket.timeout:
                    continue
                s.settimeout(None)
                تحديث_الواجهة(f"🔗 متصل من {عنوان[0]}")

                try:
                    استقبال_ملف(اتصال, مجلد_الحفظ, عنوان[0])
                except Exception as e:
                    تحديث_الواجهة(f"❌ خطأ أثناء الاستقبال: {e}")
                finally:
                    اتصال.close()
                    تحديث_الواجهة(f"🟢 في الانتظار على {ip}:{منفذ}")

            s.close()
            تحديث_الواجهة("⏹️ توقف الخادم")
        except Exception as e:
            تحديث_الواجهة(f"❌ خطأ في الخادم: {e}")

    threading.Thread(target=خادم, daemon=True).start()

def استقبال_ملف(اتصال, مجلد_الحفظ, عنوان_المرسل):
    # اسم الملف — يُقبل كما هو تمامًا بدون أي فلترة أو تعديل
    اسم_الملف = اتصال.recv(4096).decode()
    اتصال.send(b"ok1")

    # حجم الملف
    حجم_الملف = int(اتصال.recv(1024).decode())
    اتصال.send(b"ok2")

    المسار = os.path.join(مجلد_الحفظ, اسم_الملف)

    # لو الملف موجود: نسأل المستخدم يخلي الأمر بمزاجه (استبدال / تسمية / إلغاء)
    if os.path.exists(المسار):
        الرد = simpledialog.askstring(
            "الملف موجود",
            f"'{اسم_الملف}' موجود بالفعل.\\n"
            f"اكتب: r = استبدال | n = حفظ بنسخة جديدة | أي شيء آخر = إلغاء"
        )
        if الرد and الرد.lower() == "r":
            pass  # استبدال — بمزاج المستخدم
        elif الرد and الرد.lower() == "n":
            اسم_القاعدة, امتداد = os.path.splitext(اسم_الملف)
            رقم = 1
            while os.path.exists(المسار):
                المسار = os.path.join(مجلد_الحفظ, f"{اسم_القاعدة} ({رقم}){امتداد}")
                رقم += 1
        else:
            اتصال.send(b"cancel")
            تحديث_الواجهة("🚫 تم إلغاء استقبال الملف")
            return

    اتصال.send(b"ok3")

    استلمت = 0
    وقت_البدء = time.time()
    with open(المسار, "wb") as f:
        while استلمت < حجم_الملف:
            بيانات = اتصال.recv(حجم_القطعة)
            if not بيانات:
                break
            f.write(بيانات)
            استلمت += len(بيانات)
            تحديث_التقدم(استلمت, حجم_الملف)

    الوقت = time.time() - وقت_البدء
    سرعة = تنسيق_الحجم(حجم_الملف / الوقت) + "/ثانية" if الوقت > 0 else "—"
    تحديث_الواجهة(f"✅ تم استلام: {اسم_الملف} ({تنسيق_الحجم(حجم_الملف)}) | {سرعة}")
    messagebox.showinfo("تم الاستلام", f"✅ {اسم_الملف}\\nالحجم: {تنسيق_الحجم(حجم_الملف)}\\nالسرعة: {سرعة}\\nمن: {عنوان_المرسل}")

def إيقاف_الاستقبال():
    global خادم_يعمل
    خادم_يعمل = False
    تحديث_الواجهة("⏹️ جاري إيقاف الخادم...")

# ------------ إرسال الملفات ------------ #
إلغاء_الإرسال = False

def بدء_ارسال():
    global إلغاء_الإرسال
    اختيار = messagebox.askyesnocancel("نوع النقل", "هل تريد إرسال مجلد كامل؟\\nنعم = مجلد | لا = ملف واحد | إلغاء = خروج")
    if اختيار is None:
        return
    elif اختيار:  # مجلد
        مسار_المصدر = filedialog.askdirectory(title="اختر المجلد للإرسال")
    else:  # ملف
        مسار_المصدر = filedialog.askopenfilename(title="اختر الملف للإرسال")

    if not مسار_المصدر:
        return

    ip_المستقبل = simpledialog.askstring("ادخل IP", "ادخل عنوان IP للجهاز المستقبل:")
    if not ip_المستقبل:
        return

    إلغاء_الإرسال = False
    # الإرسال في خيط منفصل — لا تجميد للواجهة أبدًا
    threading.Thread(target=ارسال_ملف, args=(مسار_المصدر, ip_المستقبل), daemon=True).start()

def إلغاء_عملية_الإرسال():
    global إلغاء_الإرسال
    إلغاء_الإرسال = True

def ارسال_ملف(مسار_المصدر, ip_المستقبل):
    مسار_الإرسال = مسار_المصدر
    اسم_الملف = os.path.basename(مسار_المصدر)
    هو_مجلد_مضغوط = False

    # لو مجلد: نضغطه مؤقتًا ثم نرسله
    if os.path.isdir(مسار_المصدر):
        تحديث_الواجهة("🗜️ جاري ضغط المجلد...")
        مسار_الإرسال = مسار_المصدر + ".zip"
        اسم_الملف += ".zip"
        with zipfile.ZipFile(مسار_الإرسال, "w", zipfile.ZIP_DEFLATED) as z:
            for جذر, مجلدات, ملفات in os.walk(مسار_المصدر):
                for م in ملفات:
                    كامل = os.path.join(جذر, م)
                    z.write(كامل, os.path.relpath(كامل, مسار_المصدر))
        هو_مجلد_مضغوط = True

    حجم_الملف = os.path.getsize(مسار_الإرسال)

    try:
        s = socket.socket()
        s.connect((ip_المستقبل, 5001))

        # 1) اسم الملف كما هو
        s.send(اسم_الملف.encode())
        if s.recv(3) != b"ok1":
            raise Exception("رفض المستقبل اسم الملف")
        # 2) الحجم
        s.send(str(حجم_الملف).encode())
        if s.recv(3) != b"ok2":
            raise Exception("رفض المستقبل حجم الملف")
        # 3) موافقة نهائية (حالة وجود ملف بنفس الاسم)
        الرد = s.recv(6)
        if الرد == b"cancel":
            raise Exception("المرسل إليه ألغى الاستقبال")

        أرسلت = 0
        وقت_البدء = time.time()
        with open(مسار_الإرسال, "rb") as f:
            while أرسلت < حجم_الملف:
                if إلغاء_الإرسال:
                    s.close()
                    تحديث_الواجهة("🚫 تم إلغاء الإرسال")
                    return
                بيانات = f.read(حجم_القطعة)
                if not بيانات:
                    break
                s.send(بيانات)
                أرسلت += len(بيانات)
                تحديث_التقدم(أرسلت, حجم_الملف)

        s.close()
        الوقت = time.time() - وقت_البدء
        سرعة = تنسيق_الحجم(حجم_الملف / الوقت) + "/ثانية" if الوقت > 0 else "—"
        تحديث_الواجهة(f"✅ تم الإرسال: {اسم_الملف} | {سرعة}")
        messagebox.showinfo("تم", f"✅ تم الإرسال بنجاح!\\n{اسم_الملف}\\nالحجم: {تنسيق_الحجم(حجم_الملف)}\\nالسرعة: {سرعة}")

    except Exception as e:
        تحديث_الواجهة(f"❌ فشل الإرسال: {e}")
        messagebox.showerror("خطأ", f"❌ فشل الإرسال: {e}")
    finally:
        if هو_مجلد_مضغوط and os.path.exists(مسار_الإرسال):
            os.remove(مسار_الإرسال)  # حذف الملف المؤقت المضغوط

# ------------ واجهة المستخدم ------------ #
واجهة = tk.Tk()
واجهة.title("📁 نقل الملفات محليًا — النسخة المحسّنة")
واجهة.geometry("520x420")

عنوان = tk.Label(واجهة, text="نقل الملفات بين جهازين عبر الشبكة المحلية", font=("Arial", 14, "bold"))
عنوان.pack(pady=10)

ip_الجهاز = الحصول_على_عنوان_IP()
tk.Label(واجهة, text=f"🌐 IP جهازك: {ip_الجهاز}", font=("Arial", 11), fg="green").pack()

زر_استقبال = tk.Button(واجهة, text="📥 استقبال ملفات", font=("Arial", 13), bg="#e8f5e9", command=بدء_استقبال)
زر_استقبال.pack(pady=8, fill="x", padx=40)

زر_ارسال = tk.Button(واجهة, text="📤 إرسال ملف / مجلد", font=("Arial", 13), bg="#e3f2fd", command=بدء_ارسال)
زر_ارسال.pack(pady=8, fill="x", padx=40)

زر_إلغاء_الإرسال = tk.Button(واجهة, text="🚫 إلغاء الإرسال الحالي", font=("Arial", 11), bg="#ffebee", command=إلغاء_عملية_الإرسال)
زر_إلغاء_الإرسال.pack(pady=4, fill="x", padx=60)

زر_إيقاف_الخادم = tk.Button(واجهة, text="⏹️ إيقاف وضع الاستقبال", font=("Arial", 11), bg="#fff3e0", command=إيقاف_الاستقبال)
زر_إيقاف_الخادم.pack(pady=4, fill="x", padx=60)

شريط_التقدم = ttk.Progressbar(واجهة, orient="horizontal", length=400, mode="determinate")
شريط_التقدم.pack(pady=10)

نسبة_النقل = tk.Label(واجهة, text="0%", font=("Arial", 12, "bold"))
نسبة_النقل.pack()

الحالة = tk.Label(واجهة, text="", font=("Arial", 11), fg="blue", wraplength=480)
الحالة.pack(pady=15)

tk.Label(واجهة, text="💡 تأكد أن الجهازان على نفس الشبكة وافتح المنفذ 5001 بالجدار الناري",
         font=("Arial", 9), fg="gray").pack(side="bottom", pady=5)

واجهة.mainloop()
