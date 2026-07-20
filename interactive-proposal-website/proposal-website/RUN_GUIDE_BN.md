# বাংলা Run, Customize, GitHub ও Live Deploy Guide

## ১. প্রথমবার কম্পিউটারে চালানো

ZIP extract করে `proposal-website` folder VS Code-এ খোলো। তারপর Terminal-এ:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Browser-এ খোলো:

```text
http://127.0.0.1:5000
```

Server বন্ধ করতে Terminal-এ `Ctrl + C` চাপবে।

## ২. নিজের নাম ও লেখা পরিবর্তন

শুধু `config.json` file edit করলেই হবে। প্রধান অংশগুলো:

```json
"recipient_name": "যাকে proposal দেবে তার নাম",
"sender_name": "তোমার নাম"
```

একই file থেকে proposal text, emoji, button label, time, food এবং সব color পরিবর্তন করা যায়। পরিবর্তনের পর server restart করবে।

## ৩. Fee random রাখা

`config.json`-এ:

```json
"mode": "random",
"random_min": 199,
"random_max": 999,
"random_step": 50
```

প্রতিবার fee screen খুললে Python range থেকে একটি random value পাঠাবে।

## ৪. Fee নিজের ইচ্ছামতো fixed করা

```json
"mode": "fixed",
"fixed_amount": 499
```

এখানে `499` বদলে যেকোনো positive number লিখতে পারো। এটি শুধু joke fee—website কোনো real payment নেয় না।

## ৫. Response দেখা

কেউ final confirmation করলে date, time এবং food SQLite database-এ save হবে। দেখতে:

```powershell
flask --app app responses
```

## ৬. GitHub-এ push করা

GitHub-এ empty repository তৈরি করো। Repository folder-এর Terminal-এ:

```bash
git init
git add .
git commit -m "Build interactive proposal website"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

`YOUR_USERNAME` এবং `YOUR_REPOSITORY` নিজের তথ্য দিয়ে বদলাবে।

## ৭. Render-এ live করা

1. Project GitHub-এ push করো।
2. `https://render.com`-এ account খোলো।
3. **New → Blueprint** নির্বাচন করো।
4. GitHub repository connect করো।
5. Render project-এর `render.yaml` ও `Dockerfile` নিজে detect করবে।
6. Deploy শেষ হলে একটি public `onrender.com` link পাবে।

Free Render service কিছুক্ষণ ব্যবহার না হলে sleep করতে পারে; পরে link খুললে আবার চালু হবে। Free filesystem restart হলে saved SQLite response হারাতে পারে—স্থায়ী history দরকার হলে persistent disk/database ব্যবহার করবে।

## ৮. Test চালানো

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

সব ঠিক থাকলে `7 passed` দেখাবে। GitHub Actions-ও প্রতিবার push করার পর একই test চালাবে।
