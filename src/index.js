const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const PptxGenJS = require("pptxgenjs");
const { MongoClient } = require("mongodb");
const { Telegraf, Markup } = require("telegraf");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });
const express = require("express");
const app = express();
const BOT_TOKEN = process.env.BOT_TOKEN;
const GROQ_API_KEY = process.env.GROQ_API_KEY;
const GROQ_MODEL = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";
const MONGODB_URI = process.env.MONGODB_URI;
const MONGODB_DB_NAME = process.env.MONGODB_DB_NAME || "slaydbot";
const ADMIN_IDS = parseAdminIds(process.env.ADMIN_IDS);
const MIN_SLIDES = 5;
const MAX_SLIDES = 15;
const SLIDE_THEMES = [
  { accent: "1D4ED8", soft: "DBEAFE", dark: "0F172A" },
  { accent: "0F766E", soft: "CCFBF1", dark: "132A28" },
  { accent: "6366F1", soft: "EEF2FF", dark: "312E81" },
];
const BUSINESS_FLOW = [
  "Kirish va kontekst",
  "Asosiy muammo",
  "Bozor yoki holat tahlili",
  "Strategik yechimlar",
  "Kanallar va taktika",
  "Kutiladigan natijalar",
  "Amalga oshirish rejasi",
  "Xatarlar va ehtiyot choralari",
  "Metrikalar va KPI",
  "Xulosa va tavsiyalar",
];

app.get("/", (req, res) => {
  res.send("Bot ishlga tushdi! ✅");
});

app.listen(3000, () => {
  console.log("Server is running on port 3000");
});

if (!BOT_TOKEN || BOT_TOKEN === "telegram_bot_token_here") {
  throw new Error("BOT_TOKEN topilmadi. .env faylga qo'shing.");
}

if (!GROQ_API_KEY || GROQ_API_KEY === "your_groq_api_key_here") {
  throw new Error("GROQ_API_KEY topilmadi. .env faylga qo'shing.");
}

if (!MONGODB_URI || MONGODB_URI === "your_mongodb_connection_string_here") {
  throw new Error("MONGODB_URI topilmadi. .env faylga qo'shing.");
}

if (ADMIN_IDS.length === 0) {
  throw new Error(
    "ADMIN_IDS topilmadi. .env faylga kamida bitta admin ID qo'shing.",
  );
}

const bot = new Telegraf(BOT_TOKEN);
const mongoClient = new MongoClient(MONGODB_URI);
const outputDir = path.join(process.cwd(), "output");
const userSessions = new Map();
let usersCollection;

if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

bot.use(async (ctx, next) => {
  if (ctx.from && usersCollection) {
    await upsertUser(ctx.from);
  }
  return next();
});

bot.start(async (ctx) => {
  userSessions.delete(ctx.from.id);
  await ctx.reply(
    `🚀 Salom! ${ctx.from.first_name} xush kelibsiz.\n\nQuyidagilardan birini tanlang:`,
    Markup.keyboard([["📊 Slayd yaratish", "💬 AI bilan suhbat"]]).resize(),
  );
});

bot.help(async (ctx) => {
  await ctx.reply(
    `❓ Yordam:\n\n1. "📊 Slayd yaratish" ni tanlang.\n2. Mavzu yuboring.\n3. Slaydlar sonini (${MIN_SLIDES}-${MAX_SLIDES}) kiriting.\n4. Tayyor faylni yuklab oling.\n\n"💬 AI bilan suhbat" orqali istalgan savolingizga javob olishingiz mumkin.`,
  );
});

bot.command("cancel", async (ctx) => {
  userSessions.delete(ctx.from.id);
  await ctx.reply(
    "✅ Joriy amal bekor qilindi.",
    Markup.keyboard([["📊 Slayd yaratish", "💬 AI bilan suhbat"]]).resize(),
  );
});

bot.command("admin", async (ctx) => {
  if (!isAdmin(ctx.from.id)) {
    return ctx.reply("⚠️ Sizda admin huquqi yo'q.");
  }

  userSessions.delete(ctx.from.id);
  await ctx.reply(
    "⚙️ Admin panel:\n\n/stats - userlar statistikasi\n/broadcast - xabar yuborish\n/cancel - bekor qilish",
  );
});

async function handleAIChat(ctx, text) {
  try {
    const response = await fetch(
      "https://api.groq.com/openai/v1/chat/completions",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${GROQ_API_KEY}`,
        },
        body: JSON.stringify({
          model: GROQ_MODEL,
          messages: [{ role: "user", content: text }],
        }),
      },
    );

    if (!response.ok) throw new Error("AI Chat error");

    const data = await response.json();
    const reply = data.choices[0].message.content;
    await ctx.reply(`🤖 AI:\n\n${reply}`, {
      reply_markup: {
        inline_keyboard: [
          [{ text: "Chatni tugatish ❌", callback_data: "end_chat" }],
        ],
      },
    });
  } catch (error) {
    console.error("Chat error:", error);
    await ctx.reply("⚠️ Kechirasiz, AI bilan bog'lanishda xatolik yuz berdi.");
  }
}

bot.action("end_chat", async (ctx) => {
  userSessions.delete(ctx.from.id);
  await ctx.answerCbQuery();
  await ctx.reply(
    "✅ Chat yakunlandi.",
    Markup.keyboard([["📊 Slayd yaratish", "💬 AI bilan suhbat"]]).resize(),
  );
});

bot.command("stats", async (ctx) => {
  if (!isAdmin(ctx.from.id)) {
    return ctx.reply("⚠️ Sizda admin huquqi yo'q.");
  }

  const [totalUsers, blockedUsers, activeUsers] = await Promise.all([
    usersCollection.countDocuments({}),
    usersCollection.countDocuments({ isBlocked: true }),
    usersCollection.countDocuments({ isBlocked: { $ne: true } }),
  ]);

  await ctx.reply(
    `📊 Bot statistikasi:\n\nJami userlar: ${totalUsers}\nFaol userlar: ${activeUsers}\nBotni bloklaganlar: ${blockedUsers}`,
  );
});

bot.command("broadcast", async (ctx) => {
  if (!isAdmin(ctx.from.id)) {
    return ctx.reply("⚠️ Sizda admin huquqi yo'q.");
  }

  userSessions.set(ctx.from.id, { step: "awaiting_broadcast_message" });
  await ctx.reply(
    "📢 Barcha userlarga yuboriladigan xabarni jo'nating.\n\nBekor qilish uchun /cancel bosing.",
  );
});

bot.on("message", async (ctx) => {
  const userId = ctx.from.id;
  const session = userSessions.get(userId);
  const text = getMessageText(ctx.message);

  if (text && text.startsWith("/") && !session) {
    return;
  }

  if (session?.step === "awaiting_broadcast_message") {
    if (!isAdmin(userId)) {
      userSessions.delete(userId);
      return;
    }

    await handleBroadcast(ctx);
    return;
  }

  if (text === "📊 Slayd yaratish") {
    userSessions.set(userId, { step: "awaiting_presentation_topic" });
    await ctx.reply(
      "✍️ Prezentatsiya mavzusini yuboring:",
      Markup.removeKeyboard(),
    );
    return;
  }

  if (text === "💬 AI bilan suhbat") {
    userSessions.set(userId, { mode: "chat" });
    await ctx.reply(
      "🤖 Men tayyorman! Istalgan savolingizni bering. Chatni to'xtatish uchun /cancel bosing.",
      Markup.removeKeyboard(),
    );
    return;
  }

  if (session?.mode === "chat") {
    await ctx.sendChatAction("typing");
    await handleAIChat(ctx, text);
    return;
  }

  if (!text) {
    await ctx.reply("⚠️ Iltimos, matn ko'rinishida xabar yuboring.");
    return;
  }

  if (session?.step === "awaiting_presentation_topic") {
    userSessions.set(userId, { step: "awaiting_slide_count", topic: text });
    await ctx.reply(
      `✅ Mavzu qabul qilindi: ${text}\n\n🔢 Slaydlar sonini yuboring (${MIN_SLIDES}-${MAX_SLIDES}):`,
    );
    return;
  }

  if (session?.step === "awaiting_slide_count") {
    const slideCount = Number.parseInt(text, 10);

    if (
      !Number.isInteger(slideCount) ||
      slideCount < MIN_SLIDES ||
      slideCount > MAX_SLIDES
    ) {
      await ctx.reply(
        `⚠️ Iltimos, faqat ${MIN_SLIDES} dan ${MAX_SLIDES} gacha bo'lgan son yuboring.`,
      );
      return;
    }

    const waitingMessage = await ctx.reply(
      "⌛ Prezentatsiya tayyorlanmoqda. SlydAI slayd matnlarini yozmoqda...",
    );

    try {
      const presentation = await generatePresentationOutline(
        session.topic,
        slideCount,
      );
      const filePath = await buildPresentationFile(
        session.topic,
        presentation,
        slideCount,
      );

      await ctx.telegram.editMessageText(
        ctx.chat.id,
        waitingMessage.message_id,
        undefined,
        "✅ Prezentatsiya tayyor bo'ldi. Faylni yuboryapman...",
      );

      await ctx.replyWithDocument(
        {
          source: filePath,
          filename: `${sanitizeFileName(session.topic)}.pptx`,
        },
        {
          caption: `Mavzu: ${session.topic}\nSlaydlar soni: ${slideCount}`,
        },
      );

      await ctx.reply(
        "Yana nima qilamiz?",
        Markup.keyboard([["📊 Slayd yaratish", "💬 AI bilan suhbat"]]).resize(),
      );

      userSessions.delete(userId);
    } catch (error) {
      console.error("Xatolik:", error);
      await ctx.telegram.editMessageText(
        ctx.chat.id,
        waitingMessage.message_id,
        undefined,
        "❌ Xatolik yuz berdi. Iltimos, keyinroq yana urinib ko'ring.",
      );
      userSessions.delete(userId);
    }
    return;
  }

  await ctx.reply(
    "🤔 Nima qilishni xohlaysiz?",
    Markup.keyboard([["📊 Slayd yaratish", "💬 AI bilan suhbat"]]).resize(),
  );
});
bot.catch((error) => {
  console.error("Telegram bot xatoligi:", error);
});

process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));

startApp().catch((error) => {
  console.error("Botni ishga tushirishda xatolik:", error);
  process.exit(1);
});

async function startApp() {
  await mongoClient.connect();
  const database = mongoClient.db(MONGODB_DB_NAME);
  usersCollection = database.collection("users");
  await usersCollection.createIndex({ telegramId: 1 }, { unique: true });
  await usersCollection.createIndex({ isBlocked: 1 });

  await bot.launch();
  console.log("Bot ishga tushdi.");
}

async function upsertUser(user) {
  const now = new Date();
  await usersCollection.updateOne(
    { telegramId: user.id },
    {
      $set: {
        telegramId: user.id,
        username: user.username || null,
        firstName: user.first_name || null,
        lastName: user.last_name || null,
        isBlocked: false,
        lastSeenAt: now,
        updatedAt: now,
      },
      $setOnInsert: {
        createdAt: now,
      },
    },
    { upsert: true },
  );
}

async function markUserBlocked(telegramId, isBlocked) {
  await usersCollection.updateOne(
    { telegramId },
    {
      $set: {
        isBlocked,
        updatedAt: new Date(),
      },
    },
  );
}

async function handleBroadcast(ctx) {
  const adminId = ctx.from.id;
  const waitingMessage = await ctx.reply(
    "⌛ Broadcast boshlandi. Xabarlar yuborilyapti...",
  );
  const users = await usersCollection
    .find({}, { projection: { telegramId: 1 } })
    .toArray();

  let sentCount = 0;
  let blockedCount = 0;
  let failedCount = 0;

  for (const user of users) {
    try {
      await ctx.telegram.copyMessage(
        user.telegramId,
        ctx.chat.id,
        ctx.message.message_id,
      );
      await markUserBlocked(user.telegramId, false);
      sentCount += 1;
    } catch (error) {
      if (isBlockedError(error)) {
        blockedCount += 1;
        await markUserBlocked(user.telegramId, true);
      } else {
        failedCount += 1;
      }
    }
  }

  userSessions.delete(adminId);
  await ctx.telegram.editMessageText(
    ctx.chat.id,
    waitingMessage.message_id,
    undefined,
    `✅ Broadcast tugadi.\n\nYuborildi: ${sentCount}\nBloklaganlar: ${blockedCount}\nXatoliklar: ${failedCount}`,
  );
}

async function generatePresentationOutline(topic, slideCount) {
  const prompt = `
Sen professional prezentatsiya yozuvchisisan.
Foydalanuvchi mavzusi asosida ${slideCount} ta slayddan iborat prezentatsiya tayyorla.

Talablar:
- Faqat JSON qaytar.
- JSON quyidagi formatda bo'lsin:
{
  "title": "umumiy prezentatsiya sarlavhasi",
  "subtitle": "qisqa izoh",
  "slides": [
    {
      "title": "slayd sarlavhasi",
      "description": "slayd mazmunini 2 ta qisqa gap bilan tushuntiruvchi izoh",
      "points": [
        {
          "title": "qisqa sarlavha",
          "text": "28-52 ta so'zdan iborat, 3-4 qatorga sig'adigan mazmunli izoh"
        }
      ]
    }
  ]
}
- Prezentatsiya biznes mantiqida qurilsin.
- Slaydlar imkon qadar quyidagi oqim bo'yicha ketsin: ${buildFlowGuide(slideCount)}.
- Har bir slaydda 3 tadan 4 tagacha points bo'lsin.
- Har bir point ichida alohida title va text bo'lsin.
- Har bir text 28-52 ta so'z oralig'ida bo'lsin va slaydda 3-4 qator ko'rinishida chiqadigan darajada mazmunli bo'lsin.
- Har bir slayd uchun description qismi bo'lsin va u mavzuni mazmunli ochib bersin.
- Matn o'zbek tilida bo'lsin.
- Mazmun sodda emas, boy va tushunarli bo'lsin.
- Har slaydda fakt, izoh, amaliy foyda yoki misol darajasidagi ma'lumot bo'lsin.
- Slaydlar bir-birini takrorlamasin, mantiqiy ketma-ketlikda bo'lsin.
- Juda uzun satrlar yozma, lekin faqat 1-2 so'zli juda qisqa iboralar ham yozma.
- Oxirgi slayd albatta xulosa bo'lsin.
- slides massivida aynan ${slideCount} ta slayd bo'lsin.
- DIQQAT: Oxirgi (xulosa) slaydning 'description' qismi juda batafsil bo'lsin, kamida 250-300 ta so'zdan iborat bo'lib, butun slaydni matn bilan to'liq to'ldirsin. Xulosada mavzuning barcha jihatlari qamrab olinsin va mazmunli yakun yasalsin.
- Sarlavhalar tabiiy va professional bo'lsin, bir xil qolip takrorlanmasin.

Mavzu: ${topic}
`.trim();

  const response = await fetch(
    "https://api.groq.com/openai/v1/chat/completions",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${GROQ_API_KEY}`,
      },
      body: JSON.stringify({
        model: GROQ_MODEL,
        temperature: 0.7,
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            content:
              "Sen qisqa, aniq va strukturalangan prezentatsiyalar yozadigan yordamchisan.",
          },
          {
            role: "user",
            content: prompt,
          },
        ],
      }),
    },
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Groq API xatoligi: ${response.status} ${errorText}`);
  }

  const data = await response.json();
  const content = data?.choices?.[0]?.message?.content;

  if (!content) {
    throw new Error("Groq javobida content yo'q.");
  }

  const parsed = JSON.parse(content);

  if (
    !parsed.title ||
    !Array.isArray(parsed.slides) ||
    parsed.slides.length === 0
  ) {
    throw new Error("Groq noto'g'ri formatda javob qaytardi.");
  }

  parsed.slides = parsed.slides.map((slide) => ({
    title: slide.title || "Slayd",
    description: slide.description || "",
    points: Array.isArray(slide.points)
      ? slide.points.slice(0, 4).map((point) => ({
          title: point?.title || "Bo'lim",
          text: point?.text || "",
        }))
      : [],
  }));

  return parsed;
}

async function buildPresentationFile(topic, presentation, slideCount) {
  const pptx = new PptxGenJS();
  const safeName = sanitizeFileName(topic);
  const fileId = crypto.randomUUID();
  const filePath = path.join(outputDir, `${safeName}-${fileId}.pptx`);

  pptx.layout = "LAYOUT_WIDE";
  pptx.author = "SlaydBot";
  pptx.company = "SlaydBot";
  pptx.subject = topic;
  pptx.title = presentation.title || topic;
  pptx.lang = "uz-UZ";
  pptx.theme = {
    headFontFace: "Aptos Display",
    bodyFontFace: "Aptos",
    lang: "uz-UZ",
  };

  const cover = pptx.addSlide();
  cover.background = { color: "F8FAFC" };
  cover.addShape("rect", {
    x: 0,
    y: 0,
    w: 13.33,
    h: 7.5,
    fill: { color: "F8FAFC" },
    line: { color: "F8FAFC" },
  });
  cover.addShape("rect", {
    x: 0,
    y: 0,
    w: 13.33,
    h: 0.45,
    fill: { color: "0F172A" },
    line: { color: "0F172A" },
  });
  cover.addShape("roundRect", {
    x: 0.85,
    y: 0.95,
    w: 0.8,
    h: 4.8,
    rectRadius: 0.05,
    fill: { color: "DBEAFE" },
    line: { color: "DBEAFE" },
  });
  cover.addShape("roundRect", {
    x: 0.85,
    y: 5.95,
    w: 11.6,
    h: 0.95,
    rectRadius: 0.04,
    fill: { color: "E2E8F0" },
    line: { color: "E2E8F0" },
  });
  cover.addText(presentation.title || topic, {
    x: 1.35,
    y: 1.15,
    w: 10.3,
    h: 1.55,
    fontSize: 26,
    bold: true,
    color: "0F172A",
    fit: "shrink",
  });
  cover.addText(
    presentation.subtitle ||
      `${topic} mavzusi bo'yicha avtomatik yaratilgan prezentatsiya`,
    {
      x: 1.38,
      y: 3.0,
      w: 8.7,
      h: 0.72,
      fontSize: 15,
      color: "334155",
      fit: "shrink",
    },
  );
  cover.addText("Strukturasi: muammo, tahlil, yechim, natija, xulosa", {
    x: 1.25,
    y: 6.25,
    w: 8.1,
    h: 0.26,
    fontSize: 12,
    color: "0F172A",
    bold: true,
  });
  cover.addText(`Slaydlar soni: ${slideCount}`, {
    x: 9.75,
    y: 6.24,
    w: 1.7,
    h: 0.26,
    fontSize: 11,
    color: "334155",
    bold: true,
    align: "right",
  });

  for (const [index, slideData] of presentation.slides
    .slice(0, slideCount)
    .entries()) {
    const theme = SLIDE_THEMES[index % SLIDE_THEMES.length];
    const slide = pptx.addSlide();
    slide.background = { color: index % 2 === 0 ? "FFFFFF" : "FCFCFD" };
    slide.addShape("rect", {
      x: 0,
      y: 0,
      w: 13.33,
      h: 0.38,
      fill: { color: theme.dark },
      line: { color: theme.dark },
    });
    slide.addText(slideData.title || "Slayd", {
      x: 0.7,
      y: 0.8,
      w: 9.4,
      h: 0.8,
      fontSize: 24,
      bold: true,
      color: theme.dark,
      fit: "shrink",
    });
    slide.addShape("roundRect", {
      x: 10.5,
      y: 0.82,
      w: 2.05,
      h: 0.42,
      rectRadius: 0.04,
      fill: { color: theme.soft },
      line: { color: theme.soft },
    });
    slide.addText(resolveSectionLabel(index, slideCount), {
      x: 10.68,
      y: 0.93,
      w: 1.7,
      h: 0.16,
      fontSize: 9.5,
      color: theme.accent,
      bold: true,
      align: "center",
    });

    const points = Array.isArray(slideData.points) ? slideData.points : [];
    const isConclusion =
      index === slideCount - 1 || /xulosa|yakun/i.test(slideData.title);
    const layoutType = isConclusion ? 3 : index % 3;

    if (layoutType === 0) {
      renderTwoColumnCards(slide, slideData, points, theme);
    } else if (layoutType === 1) {
      renderSidebarLayout(slide, slideData, points, theme);
    } else if (layoutType === 2) {
      renderGridLayout(slide, slideData, points, theme);
    } else {
      renderConclusionLayout(slide, slideData, points, theme);
    }

    slide.addShape("line", {
      x: 0.7,
      y: 6.9,
      w: 11.9,
      h: 0,
      line: { color: "CBD5E1", pt: 1.2 },
    });
    slide.addText(`${index + 1}/${slideCount}`, {
      x: 0.75,
      y: 7.0,
      w: 0.5,
      h: 0.2,
      fontSize: 9,
      color: "64748B",
    });
  }

  await pptx.writeFile({ fileName: filePath });
  return filePath;
}

function sanitizeFileName(input) {
  return (
    input
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .slice(0, 40) || "presentation"
  );
}

function renderTwoColumnCards(slide, slideData, points, theme) {
  slide.addShape("roundRect", {
    x: 0.78,
    y: 1.58,
    w: 3.15,
    h: 4.95,
    rectRadius: 0.08,
    fill: { color: theme.soft },
    line: { color: theme.soft },
  });
  slide.addText("Muhim izoh", {
    x: 1.02,
    y: 1.86,
    w: 1.45,
    h: 0.22,
    fontSize: 10,
    bold: true,
    color: theme.accent,
  });

  slide.addText(slideData.description || "", {
    x: 1.02,
    y: 2.18,
    w: 2.7,
    h: 3.85,
    fontSize: 14,
    color: theme.dark,
    bold: true,
    valign: "mid",
    fit: "shrink",
  });

  const columns = splitIntoColumns(points, 2);
  renderPointColumn(slide, columns[0], 4.25, 1.72, 3.9, theme);
  renderPointColumn(slide, columns[1], 8.35, 1.72, 3.9, theme);
}

function renderSidebarLayout(slide, slideData, points, theme) {
  slide.addShape("roundRect", {
    x: 0.8,
    y: 1.62,
    w: 4.15,
    h: 4.9,
    rectRadius: 0.08,
    fill: { color: theme.dark },
    line: { color: theme.dark },
  });

  slide.addText("Asosiy g'oya", {
    x: 1.05,
    y: 1.95,
    w: 1.8,
    h: 0.35,
    fontSize: 11,
    bold: true,
    color: "FFFFFF",
  });

  slide.addText(slideData.description || "", {
    x: 1.05,
    y: 2.35,
    w: 3.4,
    h: 3.5,
    fontSize: 15,
    color: "FFFFFF",
    fit: "shrink",
    valign: "mid",
  });

  points.slice(0, 4).forEach((point, index) => {
    const y = 1.68 + index * 1.18;
    slide.addShape("roundRect", {
      x: 5.35,
      y,
      w: 6.9,
      h: 1.08,
      rectRadius: 0.05,
      fill: { color: index % 2 === 0 ? "F8FAFC" : theme.soft },
      line: { color: "D7E2F0", pt: 1 },
    });
    slide.addText(`${index + 1}`, {
      x: 5.62,
      y: y + 0.18,
      w: 0.35,
      h: 0.24,
      fontSize: 18,
      bold: true,
      color: theme.accent,
      align: "center",
    });
    slide.addText(point.title, {
      x: 6.1,
      y: y + 0.1,
      w: 5.8,
      h: 0.24,
      fontSize: 13,
      bold: true,
      color: theme.dark,
      fit: "shrink",
      margin: 0,
    });
    slide.addText(point.text, {
      x: 6.1,
      y: y + 0.38,
      w: 5.65,
      h: 0.5,
      fontSize: 10.5,
      color: "475569",
      fit: "shrink",
      margin: 0,
      breakLine: true,
    });
  });
}

function renderGridLayout(slide, slideData, points, theme) {
  slide.addText(slideData.description || "", {
    x: 0.85,
    y: 1.52,
    w: 11.9,
    h: 0.55,
    fontSize: 12,
    color: "64748B",
    italic: true,
    fit: "shrink",
  });

  points.slice(0, 4).forEach((point, index) => {
    const isLeft = index % 2 === 0;
    const row = Math.floor(index / 2);
    const x = isLeft ? 0.9 : 6.8;
    const y = 2.0 + row * 2.1;

    slide.addShape("roundRect", {
      x,
      y,
      w: 5.55,
      h: 1.72,
      rectRadius: 0.06,
      fill: { color: row === 0 ? theme.soft : "F8FAFC" },
      line: { color: row === 0 ? theme.accent : "CBD5E1", pt: 1.2 },
    });

    slide.addText(`0${index + 1}`, {
      x: x + 0.22,
      y: y + 0.18,
      w: 0.6,
      h: 0.22,
      fontSize: 12,
      bold: true,
      color: theme.accent,
      align: "center",
    });

    slide.addText(point.title, {
      x: x + 0.32,
      y: y + 0.42,
      w: 4.85,
      h: 0.24,
      fontSize: 13,
      color: theme.dark,
      bold: true,
      fit: "shrink",
      margin: 0,
    });
    slide.addText(point.text, {
      x: x + 0.32,
      y: y + 0.74,
      w: 4.9,
      h: 0.62,
      fontSize: 10.25,
      color: "475569",
      fit: "shrink",
      margin: 0,
      breakLine: true,
    });
  });
}

function renderPointColumn(slide, items, x, startY, width, theme) {
  items.forEach((item, index) => {
    const y = startY + index * 1.55;
    slide.addShape("roundRect", {
      x,
      y,
      w: width,
      h: 1.26,
      rectRadius: 0.05,
      fill: { color: "F8FAFC" },
      line: { color: "DCE7F5", pt: 1 },
    });
    slide.addShape("ellipse", {
      x: x + 0.22,
      y: y + 0.26,
      w: 0.36,
      h: 0.36,
      fill: { color: theme.accent },
      line: { color: theme.accent },
    });
    slide.addText(item.title, {
      x: x + 0.72,
      y: y + 0.12,
      w: width - 0.95,
      h: 0.24,
      fontSize: 12.5,
      bold: true,
      color: theme.dark,
      fit: "shrink",
      margin: 0,
    });
    slide.addText(item.text, {
      x: x + 0.72,
      y: y + 0.42,
      w: width - 0.95,
      h: 0.54,
      fontSize: 10.25,
      color: "475569",
      fit: "shrink",
      margin: 0,
      breakLine: true,
    });
  });
}

function renderConclusionLayout(slide, slideData, points, theme) {
  slide.addShape("roundRect", {
    x: 0.86,
    y: 1.38,
    w: 11.5,
    h: 4.95,
    rectRadius: 0.08,
    fill: { color: "FFFFFF" },
    line: { color: "D8E1EB", pt: 1.2 },
  });
  slide.addShape("roundRect", {
    x: 1.1,
    y: 1.72,
    w: 10.95,
    h: 0.95,
    rectRadius: 0.06,
    fill: { color: theme.soft },
    line: { color: theme.soft },
  });

  slide.addText(slideData.title || "Xulosa", {
    x: 0.7,
    y: 0.8,
    w: 9.4,
    h: 0.8,
    fontSize: 24,
    bold: true,
    color: theme.dark,
    fit: "shrink",
  });

  const conclusionText = buildConclusionText(slideData, points);

  slide.addShape("roundRect", {
    x: 1.25,
    y: 3.0,
    w: 10.5,
    h: 3.5,
    rectRadius: 0.05,
    fill: { color: "F8FAFC" },
    line: { color: "D6E2F1", pt: 1 },
  });
  slide.addText(conclusionText, {
    x: 1.58,
    y: 3.1,
    w: 9.8,
    h: 3.3,
    fontSize: 12,
    color: theme.dark,
    align: "left",
    valign: "mid",
    fit: "shrink",
    breakLine: true,
    margin: 0,
  });
}

function splitIntoColumns(items, count) {
  const columns = Array.from({ length: count }, () => []);
  items.forEach((item, index) => {
    columns[index % count].push(item);
  });
  return columns;
}

function buildFlowGuide(slideCount) {
  const bodyCount = Math.max(slideCount - 1, 1);
  return BUSINESS_FLOW.slice(0, bodyCount).join(" -> ");
}

function resolveSectionLabel(index, slideCount) {
  const labels = buildFlowGuide(slideCount).split(" -> ");
  return (
    labels[index] || BUSINESS_FLOW[Math.min(index, BUSINESS_FLOW.length - 1)]
  );
}

function buildConclusionText(slideData, points) {
  // Endi AI dan kelgan description'ni o'zini qaytaramiz, chunki promptda uni uzun qilishni so'radik
  return slideData.description || "Xulosa qismi tayyorlanmoqda...";
}

function getMessageText(message) {
  return message?.text?.trim() || message?.caption?.trim() || "";
}

function parseAdminIds(value) {
  return String(value || "")
    .split(",")
    .map((item) => Number.parseInt(item.trim(), 10))
    .filter((item) => Number.isInteger(item));
}

function isAdmin(userId) {
  return ADMIN_IDS.includes(userId);
}

function isBlockedError(error) {
  const description =
    error?.response?.description || error?.description || error?.message || "";
  const code = error?.response?.error_code || error?.code;
  return (
    code === 403 || /blocked by the user|bot was blocked/i.test(description)
  );
}
