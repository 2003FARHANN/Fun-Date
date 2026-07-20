# Fun Date — Email Notification Update

এই update ব্যবহার করলে কেউ proposal flow সম্পূর্ণ করার পর নিচের তথ্য email-এ পাওয়া যাবে:

- নির্বাচিত date
- নির্বাচিত time
- food choice
- playful fee
- response ID
- submission time

## 1. File replace করুন

এই package-এর `app.py` দিয়ে আপনার project-এর নিচের file-টি replace করুন:

```text
interactive-proposal-website/proposal-website/app.py
```

অন্য কোনো file পরিবর্তন করতে হবে না।

## 2. GitHub-এ push করুন

Git Bash-এ `FunProject` folder থেকে চালান:

```bash
git add interactive-proposal-website/proposal-website/app.py
git commit -m "Add email notification for date responses"
git push origin main
```

## 3. Resend account এবং API key তৈরি করুন

1. https://resend.com এ `farhandotsikder@gmail.com` দিয়ে account খুলুন।
2. Dashboard থেকে **API Keys** খুলুন।
3. **Create API Key** চাপুন।
4. Key copy করুন। এটি সাধারণত `re_` দিয়ে শুরু হয়।

> API key কখনো `app.py`, `.env`, screenshot বা GitHub-এ দেবেন না।

## 4. Render Environment Variables যোগ করুন

Render dashboard থেকে:

**Fun-Date → Environment → Add Environment Variable**

এই তিনটি variable যোগ করুন:

```text
RESEND_API_KEY = re_your_real_api_key
NOTIFICATION_EMAIL_TO = farhandotsikder@gmail.com
NOTIFICATION_EMAIL_FROM = Fun Date <onboarding@resend.dev>
```

তারপর **Save, rebuild, and deploy** চাপুন।

## 5. Test করুন

1. https://fun-date.onrender.com খুলুন।
2. সম্পূর্ণ proposal flow শেষ করুন।
3. Gmail Inbox দেখুন। না পেলে Spam/Promotions folder দেখুন।
4. Render-এর **Logs**-এ `Email notification sent` লেখা দেখালে delivery request সফল হয়েছে।

## গুরুত্বপূর্ণ

`onboarding@resend.dev` test sender শুধু Resend account-এর নিজের email address-এ mail পাঠাতে পারে। অন্য email-এ পাঠাতে চাইলে Resend-এ নিজের domain verify করতে হবে।

Website response database-এ save হবে। Email delivery সাময়িকভাবে fail করলেও visitor-এর final page কাজ করবে এবং submission নষ্ট হবে না।
