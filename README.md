# GitHub Actions Browser Automation Studio

یک استودیوی پیشرفته و حرفه‌ای دسکتاپ بر پایه **Python** و **PySide6** برای طراحی، مدیریت، بازرسی بصری و اجرای گردش‌کارهای اتوماسیون مرورگر (**Browser Automation**) که به عنوان صفحه کنترل (**Control Plane**) عمل می‌کند و کارهای اجرایی (**Execution Plane**) را مستقیماً روی **GitHub Actions Runner (ubuntu-latest)** و با استفاده از **Playwright** و **Chromium** اجرا می‌نماید؛ بدون نیاز به هیچ VPS، سرور دائمی یا ماشین ابری دیگر.

---

## ۱. پیش‌نیازها و نصب پایتون (Python Installation)

برای اجرای برنامه نیاز به **Python 3.12 یا بالاتر** دارید:
- **ویندوز (Windows):** پایتون را از [python.org](https://www.python.org/downloads/) دانلود کرده و هنگام نصب حتماً گزینه **"Add python.exe to PATH"** را فعال کنید.
- بررسی نسخه نصب‌شده در ترمینال:
```bash
python --version
```

---

## ۲. نصب وابستگی‌ها (Dependencies Installation)

یک محیط مجازی بسازید و کتابخانه‌های مورد نیاز را نصب کنید:

```bash
# ساخت محیط مجازی
python -m venv .venv

# فعال‌سازی محیط در ویندوز (PowerShell)
.venv\Scripts\Activate.ps1

# یا در Command Prompt
.venv\Scripts\activate.bat

# نصب بسته‌های اصلی و توسعه
pip install -r requirements.txt

# نصب مرورگر Playwright برای بازرسی و تست‌های محلی
python -m playwright install chromium
```

---

## ۳. اجرای برنامه (Running the Application)

برنامه را می‌توانید از طریق ماژول اصلی یا فایل ریشه اجرا نمایید:

```bash
# روش اول: اجرای ماژولار استودیو
python -m app

# روش دوم: اسکریپت ریشه
python main.py
```

---

## ۴. ساخت GitHub Personal Access Token (PAT)

نرم‌افزار دسکتاپ برای اجرای گردش‌کارها روی GitHub Actions و دانلود آرتیفکت‌ها به یک توکن دسترسی نیاز دارد:
1. به مسیر **GitHub > Settings > Developer settings > Personal access tokens > Tokens (classic)** بروید.
2. روی **Generate new token (classic)** کلیک کنید.
3. حداقل Scopeهای زیر را انتخاب کنید:
   - `repo` (دسترسی کامل به مخازن خصوصی جهت خواندن/نوشتن گردش‌کارها و استیت‌ها)
   - `workflow` (دسترسی به dispatch و مانیتورینگ اجرای GitHub Actions)
4. توکن تولید شده (`ghp_...`) را کپی کنید.

> **نکته امنیتی:** این توکن توسط نرم‌افزار در **OS Keyring (Windows Credential Manager)** ذخیره شده و هرگز در هیچ فایلی کامیت نمی‌شود.

---

## ۵. اتصال به Private Repository

1. برنامه را باز کرده و به تب **Settings** بروید.
2. فیلدهای زیر را تکمیل کنید:
   - **GitHub Username:** نام کاربری شما
   - **Repository Owner:** مالک مخزن (معمولاً همان یوزرنیم یا سازمان)
   - **Repository Name:** نام مخزن خصوصی شما (مثلاً `my-automation-repo`)
   - **Default Branch:** شاخه اصلی (پیش‌فرض: `main`)
   - **Personal Access Token:** توکن کپی شده در مرحله قبل
3. روی دکمه **Test Connection** کلیک کنید تا اتصال و وضعیت اعتبارسنجی شود.

---

## ۶. تنظیم Secrets در گیت‌هاب (Security & Encryption Key)

برای حفظ امنیت نشست‌های مرورگر (کوکی‌ها، توکن‌های لاگین، LocalStorage):
1. در تب **Settings** روی دکمه **Generate New Key** کلیک کنید تا یک کلید رمزنگاری استاندارد Fernet تولید شود.
2. این کلید را کپی کرده و در تنظیمات مخزن گیت‌هاب خود اضافه کنید:
   - به مخزن در گیت‌هاب بروید: **Settings > Secrets and variables > Actions > New repository secret**
   - نام Secret: `BROWSER_STATE_KEY`
   - مقدار: کلید رمزنگاری تولید شده
3. دکمه **Save Settings** را در استودیو فشار دهید.

---

## ۷. اجرای اولین بازرسی صفحه (Page Inspection)

1. به تب **Browser & Inspector** بروید.
2. آدرس وب‌سایت مورد نظر (مثلاً `https://github.com`) را در نوار بالایی وارد کنید.
3. روی **Inspect on GitHub Actions 🚀** کلیک کنید (یا برای بازرسی فوری محلی بدون اتصال به شبکه روی **Local Inspect ⚡** کلیک نمایید).
4. فرآیند بازرسی اجرا شده، تصویر تمام‌صفحه لود می‌شود و عناصر DOM همراه با اسکریپت‌های کلاینت استخراج می‌گردند.
5. با کلیک روی هر عنصر در لیست یا پیش‌نمایش:
   - شناسه (`id`)، برچسب (`tag`)، کلاس‌ها، رول و متن عنصر نمایش داده می‌شود.
   - الگوریتم برنامه، سلکتورهای پایدار را رتبه‌بندی کرده و بهترین سلکتور پایدار را پیشنهاد می‌دهد.
   - با دکمه‌های سریع (`+ CLICK`, `+ TYPE`, `+ WAIT`) می‌توانید مستقیماً از روی المان اکشن بسازید.

---

## ۸. ساخت و ویرایش Workflow

1. به تب **Workflow Editor** بروید.
2. می‌توانید اکشن‌های اضافه شده را مشاهده کنید، ترتیب آن‌ها را با دکمه‌های **Move Up ↑** یا **Move Down ↓** تغییر دهید.
3. برای افزودن دستی اکشن روی **+ Add Action** کلیک کنید:
   - انواع اکشن‌های پشتیبانی‌شده: `CLICK`, `DOUBLE_CLICK`, `RIGHT_CLICK`, `TYPE`, `CLEAR`, `KEY_PRESS`, `WAIT`, `SELECT_OPTION`, `CHECK`, `SCREENSHOT`, `EXTRACT_TEXT`, `NAVIGATE`, ...
   - امکان تعریف `Fallback Selectors` در صورت شکست سلکتور اصلی
   - تنظیم زمان تاخیر، کلیدواژه‌ها، پاک‌کردن فیلد قبل از تایپ و غیره
4. گردش‌کار را با کلیک روی **Save to Repo** در مخزن خصوصی ذخیره کنید، یا با **Save JSON** یک فایل محلی بسازید.

---

## ۹. اجرای Workflow روی GitHub Actions

1. روی دکمه بزرگ **RUN WORKFLOW 🚀** کلیک کنید.
2. پنجره تایید را بپذیرید. برنامه به طور خودکار:
   - گردش کار را به عنوان رویداد `workflow_dispatch` به گیت‌هاب ارسال می‌کند.
   - به تب **Runs & History** سوییچ کرده و فرآیند زنده رانر (`ubuntu-latest`) را مانیتور می‌کند.
   - رانر گیت‌هاب مرورگر Chromium را باز کرده، نشست قبلی را بازیابی می‌کند، گام‌ها را به ترتیب اجرا می‌نماید و زمان هر گام را ثبت می‌کند.

---

## ۱۰. مشاهده Logs و دانلود Artifacts

1. در تب **Runs & History** لیست تمام اجراهای اخیر قابل مشاهده است.
2. با انتخاب یک اجرای خاص، وضعیت آن (`QUEUED`, `IN_PROGRESS`, `SUCCESS`, `FAILURE`) و زمان‌بندی هر مرحله نمایش داده می‌شود:
```text
[1] CLICK input[name='q'] -> SUCCESS (312ms)
[2] TYPE text="GitHub Actions" -> SUCCESS (87ms)
[3] KEY key=Enter -> SUCCESS (44ms)
[4] WAIT 1500 ms -> SUCCESS (1502ms)
```
3. در صورت بروز هرگونه خطا، اسکرین‌شات لحظه خطا به طور خودکار دانلود شده و در پنل نمایش داده می‌شود.
4. با کلیک روی **Download Artifacts** بسته کامل لاگ و گزارش ساختاریافته (`run_report.json`) در دایرکتوری `artifacts/` ذخیره می‌گردد.

---

## ۱۱. مدیریت پایداری نشست مرورگر (Browser Session Persistence)

- رانرهای گیت‌هاب پس از هر اجرا از بین می‌روند. استودیو نشست‌های مرورگر (Cookies و LocalStorage) را به صورت رمزنگاری‌شده در فایل `state/browser_state.enc` در مخزن شما ذخیره می‌کند.
- اجرای موفق هر جاب، استیت جدید را آپدیت کرده و با پیام `chore: persist updated browser session state [skip ci]` کامیت می‌کند.
- ویژگی `concurrency: group: browser-session` تضمین می‌کند دو جاب همزمان استیت یکدیگر را رونویسی نکنند.
- مقادیر حساس کوکی‌ها و توکن‌ها هرگز در لاگ‌های کنسول چاپ نمی‌شوند (Masked Logging).

---

## ۱۲. رفع خطاهای رایج (Troubleshooting)

| خطا | علت احتمالی | راه حل |
| :--- | :--- | :--- |
| **AuthenticationError (401)** | توکن PAT منقضی شده یا اشتباه است. | در تب Settings توکن معتبر با دسترسی‌های `repo` و `workflow` وارد کنید. |
| **RepositoryNotFoundError (404)** | نام یا مالک مخزن اشتباه است یا توکن به آن دسترسی ندارد. | نام دقیق `owner/repo` و دسترسی توکن را بررسی کنید. |
| **WorkflowDispatchError (422)** | فایل‌های گردش‌کار هنوز در برنچ پیش‌فرض مخزن کامیت نشده‌اند. | مطمئن شوید پوشه `.github/workflows/` در شاخه `main` مخزن وجود دارد و push شده است. |
| **InvalidToken / State Decryption Failure** | کلید رمزنگاری محلی با `BROWSER_STATE_KEY` در GitHub Secrets همخوانی ندارد. | کلید را دوباره از تب Settings کپی کرده و در Secrets مخزن بروزرسانی کنید. |
| **Selector Timeout Error** | المن مورد نظر در زمان تعیین‌شده لود نشده است. | زمان Timeout اکشن را افزایش دهید یا از Fallback Selectors استفاده نمایید. |

---

## ۱۳. اجرای تست‌ها (Automated Testing)

مجموعه تست‌های کامل واحد و یکپارچه‌سازی با دستور زیر اجرا می‌شوند:

```bash
pytest -v
```

تمام تست‌ها روی پایتون ۳.۱۲+، بدون وابستگی خارجی و با استفاده از Mockها و فیکسچرهای محلی اجرا می‌شوند.

---

## ۱۴. بسته‌بندی برای ویندوز (Packaging with PyInstaller)

برای ساخت فایل اجرایی مستقل بدون نیاز به پایتون:

```bash
pyinstaller app.spec
```

فایل خروجی اجرایی در مسیر `dist/BrowserAutomationStudio/BrowserAutomationStudio.exe` تولید می‌شود.
