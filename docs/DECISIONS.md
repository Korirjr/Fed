# قرارات Nova

| المجال | القرار |
| --- | --- |
| الفكرة | مشروع واحد، وWorkspaces منفصلة (App / Web / API) حسب طلب المستخدم، وعقل واحد يديرها |
| Git | كل Workspace لها مستودعها، أو كلها في مستودع واحد (المستخدم يختار). GitHub اختياري |
| محرّك الـ Agent | خاص بـ Nova، مكتوب بـ TypeScript (مكتبة Anthropic الرسمية + zod) |
| Platform API | Rust (Axum) |
| الموقع | Next.js (TypeScript)، خفيف |
| عرض الكود | تلوين على السيرفر (syntect أو Shiki)، والواجهات ترسم الألوان فقط |
| تطبيقات المستخدمين | Expo افتراضياً؛ Native لاحقاً |
| معاينة التطبيقات | Expo Web في إطار جوال + QR (Expo Go) + Appetize للأجهزة الحقيقية |
| بيئات المستخدمين | Daytona |
| الاستضافة | Cloud Run الآن، وCloudflare أمامها؛ GKE لاحقاً مع مطوّر |
| الأسرار | Google Cloud Secret Manager |
| التطوير | Claude Code أولاً، ثم تطوير Nova داخل Nova |
