
function makeContainer() {
    var container = document.getElementById('container');
    if (container)
        return container;

    container = document.createElement('div');
    container.setAttribute('id', 'container');
    document.body.appendChild(container);

    var ads = document.createElement('div');
    ads.setAttribute('id', 'ads');
    container.appendChild(ads);

    var xml = document.createElement('pre');
    xml.setAttribute('id', 'xml');
    container.appendChild(xml);

}

function receivedAds(data) {
    makeContainer();

    // add a row for each ad
    var ads = data.ads,
        adsContainer = document.getElementById('ads');
    for (var i = 0; i < ads.length; ++i)
        adsContainer.appendChild(makeAdNode(ads[i]));

    // show XML source
    var xmlstring = '';
    var xmlData = data.sources;
    for (var i = 0; i < xmlData.length; ++i) {
        var sourceData = xmlData[i];
        xmlstring += "<p><b>" + sourceData.name + "</b>";
        xmlstring += "<br>update time: " + sourceData.updateTime;
        xmlstring += "<br>url: " + sourceData.url;
        xmlstring += "<br>keyword: " + sourceData.keyword;
        xmlstring += "<br>xml:<br>" + sourceData.xml;

    }
    document.getElementById('xml').innerHTML = xmlstring;

    updateArrow(data.adCounter);
}

function makeAdNode(ad) {
    var adNode = document.createElement('div');
    adNode.innerHTML = ad.text;
    return adNode;
}

function updateArrow(n) {
    makeContainer();

    var arrow = document.getElementById('arrow');
    if (arrow)
        arrow.parentNode.removeChild(arrow);

    if (n < 0)
        return;

    arrow = document.createElement('span');
    arrow.innerHTML = '<span style="background-color: red; font-weight: bold; color: white;">--&gt;</span>';
    arrow.setAttribute('id', 'arrow');

    var ads = document.getElementById('ads');
    var c = ads.childNodes[n];
    if (c)
        c.insertBefore(arrow, c.childNodes[0]);
    else
        console.warn('ads has ' + ads.childNodes.length + ' children but arrow n was ' + n);
}

