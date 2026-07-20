# Fun Date — Date & Time Validation Update

## কী ঠিক করা হয়েছে

- আজকের চলে যাওয়া সময় আর select করা যাবে না।
- আজকের সব configured time শেষ হয়ে গেলে minimum date স্বয়ংক্রিয়ভাবে আগামীকাল হবে।
- আগামী মাসসহ যেকোনো future date calendar থেকে select করা যাবে।
- Browser validation bypass করলেও server Bangladesh time (UTC+6) অনুযায়ী past date-time reject করবে।
- আগের email notification system অপরিবর্তিত থাকবে।

## File replace

ZIP-টি আপনার নিচের folder-এর ভেতরে extract করে overwrite করুন:

```text
interactive-proposal-website/proposal-website
```

যে দুটি code file update হবে:

```text
app.py
static/js/app.js
```

## Git push

Git Bash যদি `proposal-website` folder-এ খোলা থাকে:

```bash
git add app.py static/js/app.js
git commit -m "Fix past date and time selection"
git push origin main
```

Render-এর Auto-Deploy নতুন commit deploy করবে। Deploy live হলে browser-এ hard refresh দিন:

```text
PC: Ctrl + F5
Mobile: site cache clear করে reload
```

## Available time পরিবর্তন

Available timeগুলো `config.json`-এর `schedule.time_options` section-এ রয়েছে। উদাহরণ:

```json
{"value": "18:00", "label": "6:00 PM"}
```

নতুন সময় যোগ বা পুরোনো সময় বাদ দিলে `config.json`-ও commit ও push করতে হবে।
