# DistroChat Commands Guide | دليل أوامر ديسترو شات

This guide lists all available commands in the DistroChat system, organized by user roles.
هذا الدليل يحتوي على جميع الأوامر المتاحة في نظام DistroChat، مقسمة حسب صلاحيات المستخدمين.

---

## 1. User Commands | أوامر المستخدم العادي
Available to all registered users.
متاحة لجميع المستخدمين المسجلين.

| Command | Description | الوصف |
| :--- | :--- | :--- |
| `/help` | Show list of available commands. | يعرض قائمة التعليمات والأوامر المتاحة. |
| `/rooms` | List accessible rooms. | يعرض الغرف المتاحة لك (العامة + الخاصة بك). |
| `/who` | List online users. | يعرض قائمة بالمستخدمين المتصلين حالياً. |
| `/join <name> [pw]` | Join a room (with password if private). | الانتقال لغرفة أخرى (مع كلمة السر للغرف الخاصة). |
| `/create_room <name> [desc] [--private pw]` | Create a new room. | إنشاء غرفة جديدة (أضف `--private` للغرف الخاصة). |
| `/dm @user <msg>` | Send a direct message to a user. | إرسال رسالة خاصة لمستخدم معين. |
| `/stats` | View server statistics. | عرض إحصائيات السيرفر ونشاط الغرف. |
| `/clear` | Clear local chat screen. | مسح شاشة المحادثة لديك فقط. |
| `/quit` | Logout and disconnect. | تسجيل الخروج وإغلاق البرنامج. |

---

## 2. Moderator Commands | أوامر المشرفين
Available to Moderators and Admins.
متاحة للمشرفين والمديرين.

| Command | Description | الوصف |
| :--- | :--- | :--- |
| `/kick <user>` | Kick a user from the server. | طرد مستخدم من السيرفر فوراً. |
| `/mute <user> <sec>` | Mute a user for X seconds. | كتم صوت مستخدم لفترة زمنية محددة بالثواني. |
| `/broadcast <msg>` | Send an announcement to all rooms. | إرسال رسالة رسمية تظهر للجميع في كل الغرف. |
| `/stats` | View detailed staff statistics. | عرض إحصائيات متقدمة تشمل عناوين الـ IP. |

---

## 3. Admin Commands | أوامر الإدارة العليا
Available to Admins only.
متاحة للمديرين فقط.

| Command | Description | الوصف |
| :--- | :--- | :--- |
| `/ban <user> [reason]` | Permanently ban a user. | حظر مستخدم نهائياً من دخول السيرفر. |
| `/unban <user>` | Remove a ban from a user. | فك الحظر عن مستخدم محظور. |
| `/promote <user>` | Promote a user to Moderator. | ترقية مستخدم عادي ليكون مشرفاً (Moderator). |
| `/clear_room [name]` | Wipe chat history for a room (everyone). | مسح سجل المحادثات بالكامل في الغرفة (للجميع). |

---

### Important Notes | ملاحظات هامة:
- **Private Rooms**: Private rooms are invisible to everyone except the owner and members.
- **الغرف الخاصة**: الغرف الخاصة لا تظهر لأي شخص باستثناء صاحبها وأعضائها.
- **Auto-Join**: When you create a room, you join it automatically as the owner.
- **الدخول التلقائي**: عند إنشاء غرفة، يتم إدخالك إليها تلقائياً بصلاحية المالك.
- **Persistence**: Once you join a private room, it stays in your list permanently.
- **الاستمرارية**: بمجرد دخولك غرفة خاصة، ستظل تظهر في قائمتك دائماً للعودة إليها.
