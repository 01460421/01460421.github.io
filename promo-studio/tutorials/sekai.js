// SEKAI 資源中心：完整操作教學（約 10 分鐘）
// 每一章：{ n, title, sub, run(r) }，r 是 Recorder
const HOME = 'https://project-sekai-center.com';
const nav = (r, p, cap) => r.click(`aside [data-p="${p}"]`, cap, { wait: 1800 });
const tab = (r, name, cap, wait = 1600) => r.click(`main [role=tab]:has-text("${name}")`, cap, { wait });
const btn = (r, name, cap, wait = 1300) => r.click(`main button:has-text("${name}")`, cap, { wait });

module.exports = {
  site: HOME,
  title: 'SEKAI 資源中心',
  storage: { 'sekai-guide-hide': '1', 'sekai-hp-tip': '1', 'sekai-lang-hint': '1', 'sekai-intro': 'off' },
  intro: { hook: ['完整使用教學。', '跟著做，十分鐘上手。'], tagline: '世界計畫台服，一站全包。' },
  outro: { line: '有 AI，跑得更聰明。', cta: '立即開始' },
  chapters: [
    { title: '介面導覽', sub: '選單分類、伺服器與語言、深淺色主題', async run(r) {
      await r.say('左側是功能選單，依「主頁、追活動、圖鑑與資料、計算工具、社群」分類。');
      await r.hl('aside', 3200);
      await r.click('button:has-text("台服")', '右上角可以切換台服／日服與繁簡中文。', { wait: 1800 });
      await r.key('Escape', 500);
      await r.click('button[title*="主題"], button:has-text("主題")', '一鍵切換深色／淺色主題。', { wait: 1800 });
      await r.click('button[title*="主題"], button:has-text("主題")', '', { wait: 900 });
      await r.move('button:has-text("複製連結")'); await r.say('「複製連結」把目前頁面連同篩選條件分享出去。', 2600);
    } },
    { title: '搜尋與指令', sub: '⌘K 一鍵找到任何功能、歌曲、角色', async run(r) {
      await r.click('main button:has-text("搜尋功能")', '按 ⌘K 或點搜尋列，任何功能、歌曲、角色都找得到。', { wait: 1200 });
      await r.keys('摸魚', '輸入「摸魚」，直接跳到摸魚表。', 2200);
      await r.key('Backspace', 150); await r.key('Backspace', 300);
      await r.keys('T100', '也可以查榜線、歌曲或角色名稱。', 2400);
      await r.key('Escape', 800);
    } },
    { title: '首頁', sub: '當期活動、今日摘要、卡池與快速前往', async run(r) {
      await r.say('首頁一打開就是當期活動：剩餘時間、進度與榜線公布時間。', 3200);
      await r.move('main button:has-text("結算前提醒我")'); await r.say('「結算前提醒我」會在活動結束前通知你。', 2800);
      await r.scroll(620); await r.say('今日摘要：今天的活動、卡池與遊戲公告。', 3000);
      await r.scroll(650); await r.say('當前主要卡池與剩餘天數，點進去看完整內容。', 3000);
      await r.scroll(700); await r.say('「快速前往」一鍵到最常用的功能。', 2800);
      await r.top();
      await btn(r, '自訂首頁', '「自訂首頁」可以調整首頁要顯示哪些區塊。', 2200);
      await r.key('Escape', 700);
    } },
    { title: '活動總覽', sub: '本期活動一頁看完，還能預測未來排程', async run(r) {
      await nav(r, 'event', '進入「活動總覽」。');
      await r.say('本期活動的倒數、我的名次、榜線預測、卡池與加分卡都在這一頁。', 3000);
      await r.scroll(500, 1500); await r.top();
      await tab(r, '活動資料', '「活動資料」：活動時程、活動卡與排名獎勵。', 2400);
      await tab(r, '活動回顧', '「活動回顧」：歷代活動的結果。', 2200);
      await tab(r, '排程預測', '「排程預測」：推估台服未來活動與卡池的時間。', 2600);
      await tab(r, '日服現況', '「日服現況」：先看看日服正在跑什麼。', 2400);
    } },
    { title: '排名與榜線', sub: '即時排名、分段榜線、歷代資料與預測', async run(r) {
      await nav(r, 'rank', '進入「排名與榜線」。');
      await btn(r, '即時排名', '即時排名每分鐘更新。', 2400);
      await btn(r, '分段榜線', '分段榜線：T10、T100、T1000……各檔分數一次看。', 2600);
      await btn(r, '榜線趨勢', '榜線趨勢：看分數怎麼隨時間成長。', 2600);
      await tab(r, '榜線資料庫', '「榜線資料庫」：歷代活動的最終榜線。', 2400);
      await tab(r, '分析中心', '「分析中心」：時速、周回與終線預測。', 2600);
      await tab(r, '玩家查詢', '「玩家查詢」：輸入玩家名字或 ID 查排名紀錄。', 2400);
    } },
    { title: 'WL3 專區', sub: 'World Link 3 的時程、規則與配隊', async run(r) {
      await nav(r, 'wl3', '進入「WL3 專區」。');
      await r.say('開跑倒數、每一章的時程與規則變化，一頁看完。', 2800);
      await r.scroll(550); await r.say('滿配加成、總合力上限，以及日服每一章的最終榜線。', 3000);
      await r.top();
      await tab(r, 'WL3 計算器', '「WL3 計算器」：算出每一章主隊與後排的合計加成。', 2800);
      await tab(r, 'WL 後排加成', '「WL 後排加成」：用你的卡庫找出最佳後排。', 2600);
    } },
    { title: '日程與公告', sub: '活動日曆、卡池列表、遊戲公告', async run(r) {
      await nav(r, 'calendar', '進入「日程與公告」。');
      await r.say('活動日曆：本月每天有什麼活動與卡池。', 2400);
      await btn(r, '下月 ▶', '切換月份。', 1600);
      await btn(r, '今天', '', 1200);
      await btn(r, '生日池', '用分類標籤篩選，例如只看生日池。', 2200);
      await btn(r, '生日池', '', 900);
      await r.move('main button:has-text("匯出 .ics")'); await r.say('「匯出 .ics」可以加進自己的行事曆。', 2400);
      await tab(r, '卡池列表', '「卡池列表」：所有卡池與期間。', 2400);
      await tab(r, '遊戲公告', '「遊戲公告」：官方公告整理。', 2400);
    } },
    { title: '卡片圖鑑', sub: '依團體、角色、屬性篩選，看數值與技能', async run(r) {
      await nav(r, 'cards', '進入「卡片圖鑑」。');
      await btn(r, 'Leo/need', '先選團體……', 1500);
      await btn(r, '一歌', '再選角色，只看一歌的卡。', 2000);
      await r.click('main .cv-card >> nth=2', '點開任一張卡，看滿等數值、技能與釋出日。', { wait: 3000 });
      await r.key('Escape', 900);
      await tab(r, '卡片技能庫', '「卡片技能庫」：依技能效果找卡。', 2400);
      await tab(r, '收集率', '「收集率」：記錄你擁有哪些卡。', 2400);
    } },
    { title: '角色與收集', sub: '26 位角色的完整檔案', async run(r) {
      await nav(r, 'chars', '進入「角色與收集」。');
      await r.type('main input[type=search]', '未來', '搜尋角色名、假名或英文。', { wait: 1800 });
      await r.click('main [role=button]:has(img) >> nth=0', '點開角色：聲優、生日、身高、學校、喜好與相關卡片。', { wait: 3000 });
      await r.key('Escape', 900);
      await tab(r, '收集室', '「收集室」：角色收集進度一覽。', 2400);
    } },
    { title: '歌曲', sub: '難度與團體篩選、排序，以及原聲帶', async run(r) {
      await nav(r, 'songs', '進入「歌曲」。');
      await btn(r, 'ニーゴ', '依團體篩選。', 1800);
      await r.select('main select', { index: 2 }, '依難度排序，找出最難的歌。', { wait: 2200 });
      await btn(r, '▦', '切換成卡片檢視。', 2000);
      await btn(r, '☰', '', 900);
      await tab(r, '原聲帶', '「原聲帶」：遊戲 BGM 線上試聽——這支影片的背景音樂就是來自這裡。', 3200);
    } },
    { title: '劇情與漫畫', sub: '台服翻譯文本，可播語音', async run(r) {
      await nav(r, 'story', '進入「劇情與漫畫」。');
      await r.say('活動、主線、卡片、區域對話、個人與特別劇情，全部可以讀。', 2600);
      await r.click('main button:has-text("約定的Passerelle")', '點一個活動劇情……', { wait: 2600 });
      await r.scroll(450); await r.say('台服翻譯文本，有語音的台詞可以直接播放。', 3000);
      await r.key('Escape', 700);
      await nav(r, 'story', '', 1000);
      await tab(r, '一格漫畫', '「一格漫畫」：遊戲內的四格／一格漫畫。', 2600);
    } },
    { title: '豆森 MySekai', sub: '家具、素材與工作室', async run(r) {
      await nav(r, 'fixtures', '進入「豆森 MySekai」。');
      await btn(r, '植物', '家具圖鑑依分類篩選。', 1800);
      await r.type('main input[type=search]', '櫻', '也能搜尋家具名稱與標籤。', { wait: 2000 });
      await tab(r, '素材圖鑑', '「素材圖鑑」：製作家具需要的素材從哪裡來。', 2400);
      await tab(r, '豆森生日派對', '「豆森生日派對」：生日派對的家具與獎勵。', 2400);
    } },
    { title: '計算中心', sub: 'EP 精算、效率排行與各種試算', async run(r) {
      await nav(r, 'calc', '進入「計算中心」。');
      await btn(r, '衝 T100', '先選一個預設情境，例如「衝 T100」。', 1800);
      await r.type('main input[placeholder*="曲名"]', 'Sage', '輸入曲名關鍵字……', { wait: 1400 });
      await btn(r, 'MASTER', '選擇難度。', 1400);
      await r.click('main button:text-matches("^\\s*7\\s*×\\s*29")', '設定火數。', { wait: 1600 });
      await r.scroll(450); await r.say('單局活動 P、每小時 P 與所需時間馬上算出來。', 3000);
      await r.top();
      await btn(r, '效率排行', '「效率排行」：所有歌曲的效率比較。', 2400);
      await btn(r, '抽卡天井', '還有抽卡天井、推隊倍率、體力回復等工具。', 2400);
    } },
    { title: '摸魚表：活動 P 查詢', sub: '排行、摸魚優先、單曲查詢', async run(r) {
      await r.goto(HOME + '/ep-calc');
      await r.say('摸魚表依你的隊伍條件，算出台服每首歌、每個難度的活動 P。', 3000);
      await r.hl('fieldset >> nth=0', 2600);
      await r.select('select:has(option:text-is("每小時 P"))', { label: '每小時 P' }, '「排行」：依單局 P、每小時 P 或每體力 P 排序。', { wait: 1800 });
      await r.scroll(420); await r.say('台服全曲庫一次比完。', 2400);
      await r.top();
      await r.click('[role=tab]:has-text("摸魚優先")', '「摸魚優先」：差距在範圍內，挑出每首歌等級最低的難度。', { wait: 2000 });
      await r.scroll(420, 1600); await r.top();
      await r.click('[role=tab]:has-text("單曲查詢")', '「單曲查詢」：並列比較單一曲目所有難度。', { wait: 1200 });
      await r.type('input[list], input[placeholder*="Sage"]', 'Sage', '', { wait: 600, enter: true });
      await r.scroll(420); await r.say('曲庫每日自動更新。', 2400);
      await r.top();
      await r.click('button:has-text("複製目前條件的連結")', '「複製目前條件的連結」把你的計算條件分享給隊友。', { wait: 2200 });
      await r.goto(HOME);
    } },
    { title: '抽卡與儲值', sub: '依官方機率模擬抽卡、存石規劃', async run(r) {
      await nav(r, 'gachasim', '進入「抽卡與儲值」。');
      await r.say('依台服官方機率模型模擬抽卡，可選期數與卡池。', 2400);
      await btn(r, '10 連 保底★3↑ 3000 石', '來抽個 10 連……', 2400);
      await btn(r, '10 連 保底★3↑ 3000 石', '再一次！', 2400);
      await tab(r, '存石規劃', '「存石規劃」：算到目標卡池前能存多少石頭。', 2600);
      await tab(r, '儲值分析', '「儲值分析」：比較各種儲值方案的划算程度。', 2600);
    } },
    { title: 'Haruki 專區與 B30', sub: '用你的遊戲資料組隊、產生 Best 30 圖卡', async run(r) {
      await nav(r, 'haruki', '進入「Haruki 專區」。');
      await r.say('匯入 Haruki 工具箱的遊戲資料，算出活動最佳組卡與角色等級 EXP。', 3200);
      await r.scroll(500, 1400); await r.top();
      await nav(r, 'b30', '「B30 產生器」');
      await r.say('依你的打歌紀錄產生 Best 30 実効值圖卡，可以直接下載 PNG。', 3000);
      await r.scroll(600, 1600); await r.top();
    } },
    { title: '小遊戲與製作', sub: '猜角色、猜封面、貼圖與名片製作', async run(r) {
      await nav(r, 'guesswho', '進入「小遊戲與製作」。');
      await btn(r, '簡單（0.8×）', '「猜角色」：選難度……', 1200);
      await btn(r, '開始（10 題）', '開始 10 題挑戰！', 3200);
      await nav(r, 'guesswho', '', 1000);
      await tab(r, '貼圖製作器', '「貼圖製作器」：做自己的角色貼圖。', 2400);
      await tab(r, '名片拼圖', '「名片拼圖」：拼出你的玩家名片。', 2400);
    } },
    { title: '車隊與教學', sub: '車隊班表、123 則問答', async run(r) {
      await nav(r, 'car', '「車隊」：菜根機器人的車隊班表。');
      await r.say('三車分開排班、報班與推手標記，用 Discord 或 QQ 登入使用。', 3000);
      await nav(r, 'tut', '「教學與社群」');
      await r.say('123 則問答：養成、車隊、衝榜與音遊練習，教學圖片直接內嵌。', 3000);
      await r.scroll(600, 1500);
      await r.click('main summary >> nth=0', '點開任何一題看詳細解答。', { wait: 2400 });
      await r.top();
    } },
    { title: '線上客服與 AI 助手', sub: '小幫手即時回答，AI 助手幫你規劃', async run(r) {
      await r.click('[aria-label*="線上客服"]', '右下角的「線上客服」隨時可以打開。', { wait: 1800 });
      await r.click('button:has-text("現在的活動")', '小幫手不用登入、不花額度，點一下就回答。', { wait: 2800 });
      await r.type('textarea:visible, input[placeholder*="問我"]', 'T1000 多少', '也可以直接打字問。', { wait: 3000, enter: true });
      await r.click('button:has-text("AI 助手")', '「AI 助手」會自己查站上的榜線、卡池與你的卡，幫你規劃跑榜與抽卡。', { wait: 3400 });
      await r.say('可開「雙路並行」，同一題同時問 Claude 與 Gemini，兩邊答案並排對照。', 3200);
      await r.click('[aria-label*="線上客服"]', '', { wait: 900 });
    } },
    { title: '收藏與設定', sub: '收藏待辦、八種介面風格', async run(r) {
      await nav(r, 'favs', '「收藏與待辦」：收藏的卡、歌曲與待辦事項。');
      await r.wait(2000);
      await nav(r, 'settings', '「設定」');
      await r.say('可以換成八種不同的介面風格。', 2000);
      await btn(r, '舞台版', '例如「舞台版」……', 2400);
      await btn(r, '文青版', '或「文青版」。', 2400);
      await btn(r, '原版', '隨時換回原版。', 2000);
    } },
    { title: '特別專案', sub: '星圖、聲紋、衝榜劇場、迴響之境', async run(r) {
      for (const [p, cap] of [['x_starmap', 'SEKAI 星圖：700 多首歌化成一片可互動的星空。'], ['x_soundprint', 'SEKAI 聲紋：每首歌的聲音指紋。'], ['x_theater', '衝榜劇場：把一期活動的衝榜過程變成劇場。'], ['x_echoes', '迴響之境：探索型的互動體驗。']]) {
        await nav(r, p, cap);
        await r.wait(2600);
        await r.goto(HOME);
      }
    } },
  ],
};
