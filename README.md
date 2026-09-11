# مصادر — منصة المصادر الإسلامية الفقهية والحديثية

قاعدة معرفية موحدة تجمع المصادر الفقهية والحديثية السنية والشيعية، مع محرك زحف
محترم للمصادر الرسمية، وبحث عربي مطبّع، وطبقة RAG تُجبر Gemini على الاستناد إلى
النصوص المسترجعة من قاعدة البيانات مع استشهادات كاملة.

المشروع منظم بثلاث طبقات مستقلة:

```
Crawler Engine (Python/asyncio)
    ↓
Source Adapter (sistani الآن — إضافة مصادر جديدة دون تعديل المحرك)
    ↓
Parser → Normaliser → Database (SQLite / PostgreSQL)
    ↓
FastAPI (بحث + RAG)  ←  Next.js Frontend (RTL, dark mode)
```

## المكوّنات

| المسار | الوصف |
|---|---|
| `crawler/` | محرك الزحف العام: HTTP غير متزامن، robots.txt، معدل طلبات محافظ، إعادة محاولة بتراجع أسي، استكمال (Resume)، تجزئة SHA-256، نسخ نصية (original/search/embedding)، نسخَ تاريخية (Versioning) |
| `crawler/adapters/` | واجهة `SourceAdapter` + محول `sistani.org` + سجل المحولات |
| `backend/` | FastAPI: مسارات البيانات، البحث العربي (FTS5/tsvector)، طبقة RAG، مزوّد Gemini ببث SSE |
| `shared/` | مخطط قاعدة البيانات (SQLAlchemy 2)، معالجة النص العربي، التجزئة، فهارس البحث |
| `app/` `components/` `lib/` (الجذر) | Next.js 15 + Tailwind 4 — واجهة عربية RTL أولاً مع وضع داكن وخطوط محلية |
| `tests/` | 63 اختباراً مع HTML fixtures حقيقية من الموقع المصدر |
| `migrations/` | ترحيلات Alembic |

## مبادئ ثابتة

- **النص الأصلي مقدّس**: `text_original` يُخزّن كما ورد بأقل تعديل ممكن (تنظيف
  فراغات فقط). لا حذف تشكيل ولا تصحيح بالذكاء الاصطناعي. `text_search`
  و`text_embedding` نسخ مشتقة لا تُعرض للمستخدم.
- **لا خلط مذاهب**: فلتر المذهب جزء من استعلام البحث والاسترجاع نفسه، وليس
  تسمية في الواجهة.
- **المسألة = وحدة التخزين**: كل «مسألة N» سجل مستقل (Chunk واحد لـRAG)،
  والصفحات بلا ترقيم تُحفظ كاملة بـ`issue_number = null` حتى لا تُفقد مادة.
- **المشتقات لا تصبح مصادر**: أجوبة Gemini تُخزن في `ai_answers` منفصلة ولا
  تدخل سجلات المصادر أبداً.
- **زحف محترم**: قراءة robots.txt وتطبيقها، طلب واحد كل ثانيتين افتراضياً،
  لا تجاوز لجدران الدخول أو CAPTCHA أو حمايات المنع، Allowlist للنطاقات
  (حماية SSRF).
- **Resume**: حالة كل صفحة في `crawl_page_state` — التوقف والاستكمال لا يعيد
  الكتاب من الصفر.
- **كشف التغيير**: `content_hash` لكل سجل؛ أي تغيير حقيقي في النص يحفظ النسخة
  القديمة في `text_versions` ويرفع `source_revision` دون استبدال صامت.

## التشغيل المحلي (بلا Docker)

المتطلبات: Python 3.11+، Node 20+.

```bash
# 1) الخلفية
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"        # على ويندوز
# .venv/bin/pip install -e ".[dev]"          # على لينكس/ماك

copy .env.example .env                       # ثم املأ GEMINI_API_KEY (اختياري للبحث التقليدي)

.venv/Scripts/python -m alembic upgrade head # إنشاء المخطط
.venv/Scripts/python -m crawler seed         # البيانات المرجعية (مذاهب/مصدر/مرجع)

# 2) زحف كتاب (افتراضياً طلب واحد كل ثانيتين)
.venv/Scripts/python -m crawler crawl --source sistani --book "https://www.sistani.org/arabic/book/23720/"

# استكمال زحف متوقف، تحقق، تصدير، إحصاءات
.venv/Scripts/python -m crawler resume --source sistani --book "https://www.sistani.org/arabic/book/23720/"
.venv/Scripts/python -m crawler validate
.venv/Scripts/python -m crawler export --book-id 1
.venv/Scripts/python -m crawler stats

# 3) الـAPI
.venv/Scripts/python -m uvicorn backend.main:app --port 8000

# 4) الواجهة (Next.js في جذر المستودع)
copy .env.local.example .env.local
npm install
npm run dev
```

- الواجهة: http://localhost:3000
- الـAPI والتوثيق التفاعلي: http://localhost:8000/docs

## النشر (Deployment)

المستودع **monorepo**: الواجهة في `frontend/` والـAPI في الجذر. أي منصة نشر يجب
أن تُوجَّه للمجلد الصحيح.

### الواجهة على Cloudflare Pages

تطبيق Next.js في جذر المستودع — لا حاجة لضبط Root directory:

1. **Framework preset**: Next.js — يجعل أمر البناء: `npx @cloudflare/next-on-pages@1`
2. **Build output directory**: `.vercel/output/static` (مثبّت في `wrangler.toml`)
3. **Compatibility flags**: `nodejs_compat` (مثبّت في `wrangler.toml` أيضاً)
4. **Environment variables** (قبل البناء — متغيرات NEXT_PUBLIC تُخبز وقت البناء):
   - `NEXT_PUBLIC_API_URL` = الرابط العام للـAPI
5. تأكد أن اسم مشروع Pages يطابق `name` في `wrangler.toml`

ملاحظة: لا تستخدم أمر `npx next build` مباشرة على Cloudflare Pages — استخدم
`@cloudflare/next-on-pages` كما أعلاه لأن مسارات `/issue/[id]` و`/books/[id]`
ديناميكية وتحتاج تشغيل Next على الـWorker. ملف `.npmrc` في الجذر يعالج تعارض
`workers-types` v5 تلقائياً.

### الـAPI (Railway / Render / Fly)

- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- متغيرات البيئة: `DATABASE_URL` (رابط Neon)، `GEMINI_API_KEY`، و`BACKEND_CORS_ORIGINS`
  متضمناً دومين الواجهة النهائي (مثل `https://rtl.pages.dev`)

### الواجهة على Vercel (بديل أبسط)

Framework Preset = **Next.js** (يُكتشف تلقائياً من الجذر)، ومتغير
`NEXT_PUBLIC_API_URL`. لا حاجة لأي إعداد آخر.

## Docker (API + PostgreSQL + Frontend)

```bash
cp .env.example .env   # ضع GEMINI_API_KEY إن رغبت
docker compose up --build
```

## PostgreSQL / Neon

المشروع يدعم PostgreSQL بالكامل عبر `DATABASE_URL` (يدعم روابط Neon كما هي —
يُسقط `channel_binding` تلقائياً لأن psycopg3 لا يقبله، ويضبط `prepare_threshold=0`
لتوافق الـPooler):

```bash
# في .env
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require

.venv/Scripts/python -m alembic upgrade head   # إنشاء المخطط
.venv/Scripts/python -m crawler seed           # البيانات المرجعية
```

لنقل محتوى مزحوف سابقاً من SQLite المحلية إلى PostgreSQL دون إعادة الزحف على
المصدر (احتراماً للموقع وتوفيراً للوقت):

```bash
.venv/Scripts/python scripts/transfer_to_postgres.py "sqlite:///./data/masadir.db"
.venv/Scripts/python -c "from shared.db import fts; from shared.db.session import create_db_engine; fts.ensure_fts(create_db_engine())"
```

البحث على PostgreSQL يستخدم `to_tsvector('simple', …)` مع `ts_headline` وبنفس
المنطق: AND ثم تراجع OR، ودفعة المطابقة الحرفية، وفلاتر مذهبية صارمة داخل
الاستعلام. ملف `.env` يقرأه الزاحف والـAPI معاً وهو مستثنى من git.

## أهم مسارات الـAPI

| المسار | الوصف |
|---|---|
| `GET /api/health` | حالة الخدمة وعدد المسائل وجاهزية الذكاء الاصطناعي |
| `GET /api/books` / `GET /api/books/{id}` | المكتبة وتفاصيل الكتاب مع الفهرس الشجري |
| `GET /api/books/{id}/sections` | شجرة فهرس الكتاب (كتاب ← باب ← فصل) |
| `GET /api/issues/{id}` / `GET /api/issues/by-number/{number}` | المسألة بنصها الأصلي وميتاداتاها الكاملة |
| `GET /api/search?q=…&madhhab=…&scholar=…&book=…&issue_number=…` | بحث عربي مطبّع مع فلاتر صارمة |
| `GET /api/madhhabs` / `GET /api/scholars` / `GET /api/sources` | البيانات المرجعية |
| `POST /api/ai/ask` | «اسأل المصادر»: بث SSE بأحداث `sources` ثم `delta` ثم `done` |
| `GET /api/admin/stats` / `GET /api/admin/crawl-runs` | لوحة الإدارة |

مثال: البحث مقيداً بمذهب معين — النتائج من هذا المذهب حصراً:

```
GET /api/search?q=صيام يوم عرفة&madhhab=shia
```

## نظام النصوص الثلاثي

| العمود | الغرض | القواعد |
|---|---|---|
| `text_original` | العرض والاستشهاد | كما ورد من المصدر — لا حذف تشكيل ولا تعديل حروف |
| `text_search` | البحث النصي | تطبيع Unicode، إزالة تشكيل وتطويل، توحيد ألف/ياء/تاء/همزات، توحيد أرقام عربية/فارسية |
| `text_embedding` | البحث الدلالي وRAG | تطبيع مشابه مع الحفاظ على حدود الجمل (الحقول جاهزة لمحركات الـEmbedding وpgvector) |

## RAG والاستشهادات

سؤال المستخدم → تطبيع واسترجاع من الفهرس (مع الفلاتر الإلزامية) → بناء سياق
يتضمن لكل مسألة: المذهب، المدرسة، المرجع، الكتاب، الباب/الفصل، رقم المسألة،
النص الأصلي، الرابط الرسمي → Gemini عبر بث SSE → جواب مبثوث تدريجياً → قائمة
استشهادات مرتبطة فعلياً بالسجلات المسترجعة (وليست نصاً شكلياً).

تعليمات النظام تمنع صراحة: نسبة حكم لمرجع دون نص مسترجع، خلط المذاهب، اختراع
رقم مسألة أو رابط أو اسم كتاب، والإجابة إذا كانت المواد غير كافية.

إضافة مزوّد جديد (OpenAI/Anthropic/نموذج محلي) يتم بوراثة `backend/ai/base.py`
دون تغيير طبقة RAG.

## إضافة مصدر جديد

1. أنشئ محولاً جديداً يرث `SourceAdapter` في `crawler/adapters/` ويحدد
   `source_key` و`allowed_domains` ويجري `parse_book/parse_page/extract_records`.
2. سجّله في `crawler/adapters/registry.py`.
3. أضف سطر تسجيل في `scripts/seed_reference.py`.

المحرك الرئيسي لا يحتوي أي شرط على نوع الموقع — كل خصوصيات الموقع داخل محوله.

## جودة الكود

```bash
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m mypy crawler backend shared
.venv/Scripts/python -m pytest tests/
npm run lint && npm run typecheck && npm run build
```

## حالة ما نُفّذ فعلياً

- زحف حقيقي كامل لـ«منهاج الصالحين ـ الجزء الأول» من موقع السيستاني: 232 صفحة،
  1519 سجلاً، صفر أخطاء — موجود في `data/masadir.db` مع تصدير JSON في `exports/`.
- بحث عربي فعلي يعمل على هذه البيانات (تحقق HTTP حي)، وفلترة مذهبية صارمة.
- لوحة إدارة تعرض إحصاءات قاعدة البيانات وسجل التشغيلات والأخطاء.

ما هو جاهز بنيوياً ولم يُملأ بعد بمحتوى: الأحاديث (`hadiths` بنيتها كاملة دون
إدخال)، مقارنة المذاهب (لا بيانات سنية مجمّعة بعد — لذلك تظهر «غير متوفرة»)،
وحقول `text_embedding` (بنية جاهزة لمحرك embeddings مستقبلي).

## الحدود الأخلاقية والتقنية

الزاحف أداة أرشفة علمية محترمة: لا يتجاوز robots.txt، ولا ينتحل هوية، ولا
يتعامل مع الحجب كتحدي. المعدل الافتراضي محافظ (1 طلب/ثانيتين) وقابل للتخفيض
عبر `CRAWL_MIN_INTERVAL`. تُمنع أي محاولة لتجاوز أنظمة حماية المواقع.
