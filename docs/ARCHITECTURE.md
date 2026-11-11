# معمارية Nova (البداية)

```
المستخدم
   │
Cloudflare (حماية + DNS + SSL)
   │
Cloud Run
├── Nova Web (Next.js)
├── Platform API (Rust / Axum) ── Cloud SQL (Postgres)
└── Agent Service (TypeScript) ── Claude API
         │
      Daytona: بيئة لكل مشروع (API / Web / App)

GitHub App: ربط المستودعات (اختياري)
Secret Manager: المفاتيح وكلمات السر
```

## مسار طلب
1. الموقع يرسل الطلب إلى Platform API.
2. Platform API يتحقق من المستخدم ويحوّله إلى Agent Service.
3. الـ Agent ينشئ أو يفتح بيئة المشروع في Daytona.
4. حلقة: يسأل Claude، ينفّذ الأداة في Daytona، يبث الخطوة للمستخدم.
5. المعاينة تعرض النتيجة، ويمكن رفعها إلى GitHub.
