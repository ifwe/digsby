
function FakeTwitterSource(account, numTweets) {
    this.account = account;
    this.numTweets = numTweets;
    this.usedIds = {};
}

FakeTwitterSource.prototype = {
    fakeTweetId: function () {
        var items = this.account.feeds.timeline.items;
        var highestId = items[items.length-1].id;

        var newId = highestId + 1000;
        while (newId in this.account.tweets || newId in this.usedIds)
            newId += 1000;
        
        this.usedIds[newId] = true;
        return newId;
    },
    
    fakeUser: function () {
        var account = this.account;
        var userId;
        while (!userId || userId in account.users)
            userId = Math.floor(Math.random() * 10000000);
        return {
            "id": userId, 
            "verified": false, 
            "profile_sidebar_fill_color": "e0ff92", 
            "profile_text_color": "000000", 
            "followers_count": Math.floor(Math.random() * 500), 
            "protected": false, 
            "location": "San Diego, CA", 
            "profile_background_color": "9ae4e8", 
            "utc_offset": -28800, 
            "statuses_count": 8, 
            "description": "Classical Vocalist, Life Coach, Business Coach, Lover of Life", 
            "friends_count": 44, 
            "profile_link_color": "0000ff", 
            "profile_image_url": "http://a1.twimg.com/profile_images/467719152/Heidi-IMG_8247F-twitter_normal.jpg", 
            "notifications": null, 
            "geo_enabled": false, 
            "profile_background_image_url": "http://s.twimg.com/a/1255384803/images/themes/theme1/bg.png", 
            "screen_name": "1classicaldiva", 
            "profile_background_tile": false, 
            "favourites_count": 0, 
            "name": "Heidi Lee", 
            "url": "http://google.com", 
            "created_at": "Mon Oct 12 16:11:39 +0000 2009", 
            "time_zone": "Pacific Time (US & Canada)", 
            "profile_sidebar_border_color": "87bc44", 
            "following": null
         };
    },

    update: function(updateNotification) {
        var tweets = [];

        for (var i = 0; i < this.numTweets; ++i) {
            var date = new Date().toString().slice(0, 33);
            tweets.push({
                "favorited": false, 
                "truncated": false, 
                "text": loremIpsumParagraph(24),
                "created_at": date,
                "source": "web", 
                "in_reply_to_status_id": null, 
                "in_reply_to_screen_name": null, 
                "in_reply_to_user_id": null, 
                "geo": null, 
                "id": this.fakeTweetId(), 
                user: this.fakeUser(),
            });
        }

        console.log('created ' + tweets.length + ' fake tweets');

        var self = this, account = this.account;
        tweets = $.map(tweets, function (t) { return account.makeTweetFromNetwork(t); });
        account.newTweets(tweets, self);
        if (updateNotification)
            updateNotification.success(self, tweets);
    }
};

function fakeTweets(numTweets) {
    var src = new FakeTwitterSource(account, numTweets);
    account.maybeUpdate(false, [src]);
    account.discardOldTweets();
}


/* Lorem Ipsum Generator
 * (CC-BY) Fredrik Bridell <fredrik@bridell.com> 2009
 * Version 0.21 - multilingual
 * Released under a Creative Commons Attribution License
 *
 * You are welcome to use, share, modify, print, frame, or do whatever you like with this 
 * software, including commercial use. My only request is that you tell the world where you found it.
 * 
 * One way is to include the phrase: 
 * "Using the The Lorem Ipsum Generator by Fredrik Bridell (http://bridell.com/loremipsum/)"
 *
 * To use this on your web page: download the .js file and place it on your web server (please
 * do not include it from my server). In your html file, include the markup
 * <script type="text/javascript" src="loremipsum.js" />
 * (In the head or in the body).
 *
 * Where you want the Lorem Ipsum, include this markup:
 * <script type="text/javascript">loremIpsumParagraph(100)</script>
 * The number is the number of words in the paragraph. 
 */ 

/* Latin words, These are all the words in the first 100 lines of Ovid's Metamorphoses, Liber I. */
var latin =["ab", "aberant", "abscidit", "acervo", "ad", "addidit", "adhuc", "adsiduis", "adspirate", "aequalis", "aer", "aera", "aere", "aeris", "aestu", "aetas", "aethera", "aethere", "agitabilis", "aliis", "aliud", "alta", "altae", "alto", "ambitae", "amphitrite", "animal", "animalia", "animalibus", "animus", "ante", "aquae", "arce", "ardentior", "astra", "aurea", "auroram", "austro", "bene", "boreas", "bracchia", "caeca", "caecoque", "caeleste", "caeli", "caelo", "caelum", "caelumque", "caesa", "calidis", "caligine", "campoque", "campos", "capacius", "carentem", "carmen", "cepit", "certis", "cesserunt", "cetera", "chaos:", "cingebant", "cinxit", "circumdare", "circumfluus", "circumfuso", "coegit", "coeperunt", "coeptis", "coercuit", "cognati", "colebat", "concordi", "congeriem", "congestaque", "consistere", "contraria", "conversa", "convexi", "cornua", "corpora", "corpore", "crescendo", "cum", "cuncta", "cura", "declivia", "dedit", "deducite", "deerat", "dei", "densior", "deorum", "derecti", "descenderat", "deus", "dextra", "di", "dicere", "diffundi", "diremit", "discordia", "dispositam", "dissaepserat", "dissociata", "distinxit", "diu", "diversa", "diverso", "divino", "dixere", "dominari", "duae", "duas", "duris", "effervescere", "effigiem", "egens", "elementaque", "emicuit", "ensis", "eodem", "erant", "erat", "erat:", "erectos", "est", "et", "eurus", "evolvit", "exemit", "extendi", "fabricator", "facientes", "faecis", "fecit", "feras", "fert", "fidem", "figuras", "finxit", "fixo", "flamina", "flamma", "flexi", "fluminaque", "fontes", "foret", "forma", "formaeque", "formas", "fossae", "fratrum", "freta", "frigida", "frigore", "fronde", "fuerant", "fuerat", "fuit", "fulgura", "fulminibus", "galeae", "gentes", "glomeravit", "grandia", "gravitate", "habendum", "habentem", "habentia", "habitabilis", "habitandae", "haec", "hanc", "his", "homini", "hominum", "homo", "horrifer", "humanas", "hunc", "iapeto", "ignea", "igni", "ignotas", "illas", "ille", "illi", "illic", "illis", "imagine", "in", "inclusum", "indigestaque", "induit", "iners", "inmensa", "inminet", "innabilis", "inposuit", "instabilis", "inter", "invasit", "ipsa", "ita", "iudicis", "iuga", "iunctarum", "iussit", "lacusque", "lanient", "lapidosos", "lege", "legebantur", "levitate", "levius", "liberioris", "librata", "ligavit:", "limitibus", "liquidas", "liquidum", "litem", "litora", "locavit", "locis", "locoque", "locum", "longo", "lucis", "lumina", "madescit", "magni", "manebat", "mare", "margine", "matutinis", "mea", "media", "meis", "melior", "melioris", "membra", "mentes", "mentisque", "metusque", "militis", "minantia", "mixta", "mixtam", "moderantum", "modo", "moles", "mollia", "montes", "montibus", "mortales", "motura", "mundi", "mundo", "mundum", "mutastis", "mutatas", "nabataeaque", "nam", "natura", "naturae", "natus", "ne", "nebulas", "nec", "neu", "nisi", "nitidis", "nix", "non", "nondum", "norant", "nova", "nubes", "nubibus", "nullaque", "nulli", "nullo", "nullus", "numero", "nunc", "nuper", "obliquis", "obsistitur", "obstabatque", "occiduo", "omni", "omnia", "onerosior", "onus", "opifex", "oppida", "ora", "orba", "orbe", "orbem", "orbis", "origine", "origo", "os", "otia", "pace", "parte", "partim", "passim", "pendebat", "peragebant", "peregrinum", "permisit", "perpetuum", "persidaque", "perveniunt", "phoebe", "pinus", "piscibus", "plagae", "pluvialibus", "pluviaque", "poena", "pondere", "ponderibus", "pondus", "pontus", "porrexerat", "possedit", "posset:", "postquam", "praebebat", "praecipites", "praeter", "premuntur", "pressa", "prima", "primaque", "principio", "pro", "pronaque", "proxima", "proximus", "pugnabant", "pulsant", "quae", "quam", "quanto", "quarum", "quem", "qui", "quia", "quicquam", "quin", "quinta", "quisque", "quisquis", "quod", "quoque", "radiis", "rapidisque", "recens", "recepta", "recessit", "rectumque", "regat", "regio", "regna", "reparabat", "rerum", "retinebat", "ripis", "rudis", "sanctius", "sata", "satus", "scythiam", "secant", "secrevit", "sectamque", "secuit", "securae", "sed", "seductaque", "semina", "semine", "septemque", "sibi", "sic", "siccis", "sidera", "silvas", "sine", "sinistra", "sive", "sole", "solidumque", "solum", "sorbentur", "speciem", "spectent", "spisso", "sponte", "stagna", "sua", "subdita", "sublime", "subsidere", "sui", "suis", "summaque", "sunt", "super", "supplex", "surgere", "tanta", "tanto", "tegi", "tegit", "tellure", "tellus", "temperiemque", "tempora", "tenent", "tepescunt", "terra", "terrae", "terram", "terrarum", "terras", "terrenae", "terris", "timebat", "titan", "tollere", "tonitrua", "totidem", "totidemque", "toto", "tractu", "traxit", "triones", "tuba", "tum", "tumescere", "turba", "tuti", "ubi", "ulla", "ultima", "umentia", "umor", "unda", "undae", "undas", "undis", "uno", "unus", "usu", "ut", "utque", "utramque", "valles", "ventis", "ventos", "verba", "vesper", "videre", "vindice", "vis", "viseret", "vix", "volucres", "vos", "vultus", "zephyro", "zonae"];

/* Swedish words. These are all the words in the two first paragraphs of August Strindberg's Röda Rummet. */
var swedish = ["afton", "allm&auml;nheten", "allting", "arbetat", "att", "av", "bakom", "barège-lappar", "berberisb&auml;r", "Bergsund", "bers&aring;er", "bestr&ouml;dd", "bj&ouml;do", "blev", "blivit", "blom", "blommor", "bofinkarne", "bon", "bort", "bos&auml;ttningsbekymmer", "branta", "bygga", "b&auml;nkfot", "b&aring;de", "b&ouml;rjade", "b&ouml;rjan", "b&ouml;rjat", "Danviken", "de", "del", "deltogo", "den", "det", "detsamma", "djur", "draga", "drog", "drogos", "d&auml;r", "d&auml;rf&ouml;r", "d&auml;rifr&aring;n", "d&auml;rinne", "d&aring;", "efter", "ej", "ekl&auml;rerade", "emot", "en", "ett", "fjol&aring;rets", "fjor", "fj&auml;rran", "for", "fortsatte", "fram", "friska", "fr&aring;n", "f&auml;rd", "f&auml;stningen", "f&aring;", "f&ouml;nstervadden", "f&ouml;nstren", "f&ouml;r", "f&ouml;rbi", "f&ouml;rdes", "f&ouml;rf&auml;rligt", "f&ouml;rut", "genom", "gick", "gingo", "gjorde", "granris", "gren", "gripa", "gr&aring;sparvarne", "g&aring;", "g&aring;ngarne", "g&aring;tt", "g&ouml;mde", "hade", "halmen", "havet", "hela", "hittade", "hon", "hundar", "hus", "H&auml;stholmen", "h&aring;rtappar", "h&ouml;llo", "h&ouml;stfyrverkeriet", "i", "icke", "igen", "ilade", "illuminerade", "in", "ingen", "innanf&ouml;nstren", "Josefinadagen", "just", "kastade", "kiv", "klistringen", "kl&auml;ttrade", "knoppar", "kol", "kom", "korset", "korta", "kunde", "kvastar", "k&auml;nde", "k&auml;rleksfilter", "k&ouml;ksan", "lavkl&auml;dda", "lekte", "levdes", "Liding&ouml;skogarne", "ligger", "Liljeholmen", "lilla", "lindarne", "liv", "luften", "lukten", "l&auml;mna", "l&aring;ngt", "l&ouml;vsamlingar", "maj", "med", "medan", "mellan", "men", "moln", "Mosebacke", "mot", "m&auml;nskofot", "navigationsskolans", "nu", "n&auml;san", "obesv&auml;rat", "obrustna", "och", "ofruktsamt", "om", "os", "paljetter", "passade", "piga", "plats", "plockade", "p&auml;rontr&auml;d", "p&aring;", "rabatterna", "rakethylsor", "Riddarfj&auml;rden", "Riddarholmskyrkan", "ringdans", "rivit", "Rosendal", "rosenf&auml;rgat", "rusade", "r&ouml;karne", "saffransblommorna", "samla", "samma", "sandg&aring;ngarne", "sedan", "sig", "Sikla&ouml;n", "sin", "sina", "sista", "Sj&ouml;tullen", "Sj&ouml;tulln", "Skeppsbrob&aring;tarne", "skolan", "skr&auml;md", "skr&auml;p", "skydd", "sk&ouml;t", "slagits", "slog", "sluppit", "sluta", "snart", "sn&ouml;", "sn&ouml;dropparne", "solen", "som", "sommarn&ouml;jena", "spillror", "Stadsg&aring;rden", "stam", "stekflott", "stickorna", "stod", "stor", "stora", "stranden", "str&aring;lar", "st&ouml;rtade", "sydlig", "syrenerna", "s&aring;go", "s&aring;gsp&aring;n", "s&aring;lunda", "s&ouml;dra", "tagit", "tak", "takpannorna", "till", "tillbaka", "tittade", "tj&auml;ra", "tonade", "trampat", "tran", "tr&auml;d", "tr&auml;dg&aring;rden", "Tyskans", "t&ouml;rnade", "t&ouml;rnrosblad", "undanr&ouml;jda", "under", "unga", "upp", "uppf&ouml;r", "uppgr&auml;vda", "ur", "ut", "utefter", "utmed", "var", "Vaxholm", "verksamhet", "vilka", "vilken", "vimplarne", "vind", "vinden", "vinterns", "voro", "v&auml;gg", "v&auml;ggen", "v&auml;ntade", "&auml;nnu", "&aring;ret", "&aring;t", "&ouml;lskv&auml;ttar", "&ouml;mt&aring;ligare", "&ouml;ppnad", "&ouml;ppnades", "&ouml;ster", "&ouml;ver"];

// just switch language like this! You can also do this in a script block on the page. 
var loremLang = latin;

/* Characters to end a sentence with. Repeat for frequencies (i.e. most sentences end in a period) */
var endings = "................................??!";

/* randomly returns true with a certain chance (a percentage) */
function chance(percentage) {
	return (Math.floor(Math.random() * 100) < percentage);
}

/* capitalizes a word */
function capitalize(aString) {
	return aString.substring(0,1).toUpperCase() + aString.substring(1, aString.length);
}

/* returns a random lorem word */
function getLoremWord() {
	return loremLang[Math.floor(Math.random()*loremLang.length)];
}

function getLoremEnding() {
	var i = Math.floor(Math.random()*endings.length);
	return endings.substring(i, i+1);
}

/* inserts a number of lorem words. Does not append a space at the end. */
function loremIpsum(s, numWords) {
	for(var i=0; i<numWords-1; ++i)
        s.push(getLoremWord() + ' ');
    s.push(getLoremWord());
}

/* inserts a sentence of random words. Appends a space at the end. */
function loremIpsumSentence(s, numWords) {
	s.push(capitalize(getLoremWord()) + " ");
	loremIpsum(s, numWords-1);
    s.push(getLoremEnding());
    s.push(' ');
}

/* inserts a sentence of random words, sometimes with extra punctuation. Appends a space at the end. */
function loremIpsumSentence2(s, numWords) {
	s.push(capitalize(getLoremWord()) + " ");
	var part1 = 0;
	if(chance(50)) {
		// insert a comma or other punctuation within the sentence
		part1 = Math.floor(Math.random() * numWords-2);
		loremIpsum(s, part1);
        s.push(', ');
	} else
        s.push(' ');

	loremIpsum(s, numWords - part1 - 1);

    s.push(getLoremEnding());
    s.push(' ');
}

/* inserts a paragraph of sentences of random words. */
function loremIpsumParagraph(numWords) {
	var words = numWords;
    var s = [];
	while(words > 0){
		if(words > 10){
			w = Math.floor(Math.random() * 8) + 2;
			loremIpsumSentence2(s, w);
			words = words - w;
		} else {
			loremIpsumSentence2(s, words);
			words = 0;
		}
	}
    return s.join('');
}


function debugCounts() {
    var info = [
        'objectKeys(account.tweets).length',
        'objectKeys(account.users).length',
        'account.timeline.toInsert.length',
        'account.timeline.toDelete.length',
        'timelineWindows[0].document.all.length',
        'account.timeline.container.childNodes.length',
        'objectLength(Digsby.callbacks)',
    ];

    var infos = [];
    $.each(info, function (i, s) {
        var val = '';
        try { val = eval(s); } catch(err) {}
        infos.push(s + ': ' + val);
    });

    return infos.join('\n');
}

