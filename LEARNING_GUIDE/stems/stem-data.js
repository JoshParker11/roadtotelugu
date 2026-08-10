/* Sentence stems in English — the frames that recur constantly in everyday speech.
   Fields:
     s    = the stem (2-5 words, ___ marks the slot)
     g    = function group
     core = 1 if it belongs to the first 25
     w    = "now"  buildable with Foundational Telugu lessons 1-6
            "soon" needs the upcoming tense lessons (7-14)
     n    = optional note */

const STEMS = [

/* --- Repair & survival --- */
{s:"I don't understand", g:"Repair & survival", core:1, w:"now", n:"The single most important thing a beginner can say."},
{s:"Please say again", g:"Repair & survival", core:1, w:"now"},
{s:"Please speak slowly", g:"Repair & survival", core:1, w:"now"},
{s:"I don't know Telugu", g:"Repair & survival", core:1, w:"now"},
{s:"How do you say ___?", g:"Repair & survival", core:1, w:"now", n:"Turns any conversation into a lesson."},
{s:"What does ___ mean?", g:"Repair & survival", w:"now"},
{s:"Do you understand?", g:"Repair & survival", w:"now"},
{s:"Is that right?", g:"Repair & survival", w:"now"},
{s:"Only a little", g:"Repair & survival", w:"now"},

/* --- Identity & pointing --- */
{s:"This is ___", g:"Identity & pointing", core:1, w:"now"},
{s:"That is ___", g:"Identity & pointing", w:"now"},
{s:"This isn't ___", g:"Identity & pointing", w:"now"},
{s:"What is this?", g:"Identity & pointing", core:1, w:"now"},
{s:"What is that?", g:"Identity & pointing", w:"now"},
{s:"Which one?", g:"Identity & pointing", w:"now"},

/* --- Existence & location --- */
{s:"Where is ___?", g:"Existence & location", core:1, w:"now"},
{s:"___ is here", g:"Existence & location", w:"now"},
{s:"___ is there", g:"Existence & location", w:"now"},
{s:"There is ___", g:"Existence & location", core:1, w:"now"},
{s:"There isn't ___", g:"Existence & location", w:"now"},
{s:"Is ___ here?", g:"Existence & location", w:"now"},
{s:"Where are you?", g:"Existence & location", w:"now"},

/* --- Having --- */
{s:"I have ___", g:"Having", w:"now"},
{s:"I don't have ___", g:"Having", w:"now"},
{s:"Do you have ___?", g:"Having", w:"now"},
{s:"Who has ___?", g:"Having", w:"now"},

/* --- Wanting & needing --- */
{s:"I want ___", g:"Wanting & needing", core:1, w:"now"},
{s:"I don't want ___", g:"Wanting & needing", w:"now"},
{s:"Do you want ___?", g:"Wanting & needing", w:"now"},
{s:"What do you want?", g:"Wanting & needing", w:"now"},
{s:"I need ___", g:"Wanting & needing", w:"now"},
{s:"I need help", g:"Wanting & needing", core:1, w:"now"},

/* --- Knowing & understanding --- */
{s:"I know", g:"Knowing & understanding", core:1, w:"now"},
{s:"I don't know", g:"Knowing & understanding", core:1, w:"now"},
{s:"Do you know ___?", g:"Knowing & understanding", core:1, w:"now"},
{s:"I know a little", g:"Knowing & understanding", w:"now"},

/* --- Liking & opinion --- */
{s:"I like ___", g:"Liking & opinion", core:1, w:"now"},
{s:"I don't like ___", g:"Liking & opinion", w:"now"},
{s:"Do you like ___?", g:"Liking & opinion", w:"now"},
{s:"I think ___", g:"Liking & opinion", w:"soon"},
{s:"I think so", g:"Liking & opinion", w:"soon"},
{s:"I don't think so", g:"Liking & opinion", w:"soon"},
{s:"Is that so?", g:"Liking & opinion", w:"now"},
{s:"Maybe later", g:"Liking & opinion", w:"now"},

/* --- Ability & possibility --- */
{s:"I can ___", g:"Ability & possibility", w:"soon"},
{s:"I can't ___", g:"Ability & possibility", w:"soon"},
{s:"Can you ___?", g:"Ability & possibility", w:"soon"},
{s:"Is it possible?", g:"Ability & possibility", w:"soon"},
{s:"I can't now", g:"Ability & possibility", w:"soon"},

/* --- Requests & commands --- */
{s:"Please give me ___", g:"Requests & commands", core:1, w:"now", n:"Lesson 3's -aṇḍi rule does all the work."},
{s:"Please come here", g:"Requests & commands", w:"now"},
{s:"Please wait", g:"Requests & commands", core:1, w:"now"},
{s:"Please sit down", g:"Requests & commands", w:"now"},
{s:"Please help me", g:"Requests & commands", w:"now"},
{s:"Please don't ___", g:"Requests & commands", w:"soon"},
{s:"One moment please", g:"Requests & commands", w:"now"},
{s:"Let's go", g:"Requests & commands", w:"now"},

/* --- People & relationships --- */
{s:"Who is that?", g:"People & relationships", w:"now"},
{s:"This is my ___", g:"People & relationships", core:1, w:"now", n:"Remember the mā / nā split for family."},
{s:"___'s name is ___", g:"People & relationships", w:"now"},
{s:"Whose is this?", g:"People & relationships", w:"now"},
{s:"How many people?", g:"People & relationships", w:"now"},

/* --- Quantity & price --- */
{s:"How much is ___?", g:"Quantity & price", core:1, w:"now"},
{s:"How many ___?", g:"Quantity & price", w:"now"},
{s:"That's too much", g:"Quantity & price", w:"now"},
{s:"Only one", g:"Quantity & price", w:"now"},
{s:"A little ___", g:"Quantity & price", w:"now"},
{s:"A lot of ___", g:"Quantity & price", w:"now"},
{s:"Not enough", g:"Quantity & price", w:"now"},

/* --- Time & scheduling --- */
{s:"When is ___?", g:"Time & scheduling", w:"now"},
{s:"What time is it?", g:"Time & scheduling", w:"soon"},
{s:"___ today", g:"Time & scheduling", w:"now"},
{s:"___ tomorrow", g:"Time & scheduling", w:"now"},
{s:"___ yesterday", g:"Time & scheduling", w:"now"},
{s:"Right now", g:"Time & scheduling", w:"now"},
{s:"A little later", g:"Time & scheduling", w:"now"},
{s:"How long?", g:"Time & scheduling", w:"now"},
{s:"What day?", g:"Time & scheduling", w:"now"},

/* --- Describing things --- */
{s:"___ is good", g:"Describing things", w:"now"},
{s:"___ is very good", g:"Describing things", w:"now"},
{s:"___ is not good", g:"Describing things", w:"now"},
{s:"___ is big", g:"Describing things", w:"now"},
{s:"___ is small", g:"Describing things", w:"now"},
{s:"___ is new", g:"Describing things", w:"now"},
{s:"___ is difficult", g:"Describing things", w:"now"},
{s:"___ is easy", g:"Describing things", w:"now"},
{s:"Very ___", g:"Describing things", w:"now"},

/* --- Feelings & states --- */
{s:"I'm hungry", g:"Feelings & states", w:"now", n:"Uses the same -ku frame as wanting."},
{s:"I'm thirsty", g:"Feelings & states", w:"now"},
{s:"I'm tired", g:"Feelings & states", w:"now"},
{s:"I'm happy", g:"Feelings & states", w:"now"},
{s:"I'm not well", g:"Feelings & states", w:"now"},
{s:"I'm busy", g:"Feelings & states", w:"now"},
{s:"It's hot", g:"Feelings & states", w:"now"},
{s:"It's cold", g:"Feelings & states", w:"now"},

/* --- Social --- */
{s:"How are you?", g:"Social", core:1, w:"now"},
{s:"I'm fine", g:"Social", core:1, w:"now"},
{s:"My name is ___", g:"Social", core:1, w:"now"},
{s:"What's your name?", g:"Social", core:1, w:"now"},
{s:"Thank you", g:"Social", core:1, w:"now"},
{s:"I'm sorry", g:"Social", core:1, w:"now"},
{s:"No problem", g:"Social", w:"now"},
{s:"See you later", g:"Social", w:"now"},
{s:"Nice to meet you", g:"Social", w:"soon"},

/* --- Doing now --- */
{s:"I am ___ing", g:"Doing now", w:"soon", n:"Present continuous — lessons 7-9."},
{s:"What are you doing?", g:"Doing now", w:"soon"},
{s:"Where are you going?", g:"Doing now", w:"soon"},
{s:"I'm going to ___", g:"Doing now", w:"soon"},
{s:"He is ___ing", g:"Doing now", w:"soon"},
{s:"They are ___ing", g:"Doing now", w:"soon"},
{s:"I'm not ___ing", g:"Doing now", w:"soon"},

/* --- Past --- */
{s:"I ___ed", g:"Past", w:"soon", n:"Past tense lesson."},
{s:"Did you ___?", g:"Past", w:"soon"},
{s:"I didn't ___", g:"Past", w:"soon"},
{s:"What happened?", g:"Past", w:"soon"},
{s:"When did you ___?", g:"Past", w:"soon"},
{s:"I already ___ed", g:"Past", w:"soon"},

/* --- Future & intention --- */
{s:"I will ___", g:"Future & intention", w:"soon"},
{s:"I won't ___", g:"Future & intention", w:"soon"},
{s:"Will you ___?", g:"Future & intention", w:"soon"},
{s:"Let's ___", g:"Future & intention", w:"soon"},
{s:"Shall we ___?", g:"Future & intention", w:"soon"},
{s:"I'll come back", g:"Future & intention", w:"now", n:"You already have this — it's how Telugu says goodbye."},

/* --- Habits & routine --- */
{s:"I always ___", g:"Habits & routine", w:"soon"},
{s:"I never ___", g:"Habits & routine", w:"soon"},
{s:"I usually ___", g:"Habits & routine", w:"soon"},
{s:"Every day I ___", g:"Habits & routine", w:"soon"},
{s:"Sometimes I ___", g:"Habits & routine", w:"soon"},

/* --- Obligation & permission --- */
{s:"I have to ___", g:"Obligation & permission", w:"soon"},
{s:"I don't have to ___", g:"Obligation & permission", w:"soon"},
{s:"Do I have to ___?", g:"Obligation & permission", w:"soon"},
{s:"You should ___", g:"Obligation & permission", w:"soon"},
{s:"May I ___?", g:"Obligation & permission", w:"soon"},
{s:"Is it okay?", g:"Obligation & permission", w:"now"},

/* --- Connecting ideas --- */
{s:"___ and ___", g:"Connecting ideas", w:"now"},
{s:"___ but ___", g:"Connecting ideas", w:"now"},
{s:"Because ___", g:"Connecting ideas", w:"now"},
{s:"If ___", g:"Connecting ideas", w:"soon"},
{s:"___ also", g:"Connecting ideas", w:"now"},
{s:"More than ___", g:"Connecting ideas", w:"soon"},
{s:"___ is better", g:"Connecting ideas", w:"soon"},
{s:"After that", g:"Connecting ideas", w:"now"}
];

const GROUP_ORDER = [
  "Repair & survival","Identity & pointing","Existence & location","Having",
  "Wanting & needing","Knowing & understanding","Liking & opinion",
  "Ability & possibility","Requests & commands","People & relationships",
  "Quantity & price","Time & scheduling","Describing things","Feelings & states",
  "Social","Doing now","Past","Future & intention","Habits & routine",
  "Obligation & permission","Connecting ideas"
];
