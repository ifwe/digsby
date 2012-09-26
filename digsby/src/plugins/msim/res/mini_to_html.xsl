<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE xsl:stylesheet  [
	<!ENTITY nbsp   "&#160;">
	<!ENTITY copy   "&#169;">
	<!ENTITY reg    "&#174;">
	<!ENTITY trade  "&#8482;">
	<!ENTITY mdash  "&#8212;">
	<!ENTITY ldquo  "&#8220;">
	<!ENTITY rdquo  "&#8221;"> 
	<!ENTITY pound  "&#163;">
	<!ENTITY yen    "&#165;">
	<!ENTITY euro   "&#8364;">
]>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<xsl:output method="html" encoding="utf-8" doctype-public="-//W3C//DTD XHTML 1.0 Transitional//EN" doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"/>

<xsl:template match="/">
  <xsl:apply-templates/>
</xsl:template>


<xsl:template match="f">
<span>
    <xsl:attribute name="style" >font-family:'<xsl:value-of select="@f"/>';font-size:<xsl:value-of select="@h"/>px;<xsl:if test="(@s = 1) or (@s = 3) or (@s = 5) or (@s = 7)">font-weight:bold;</xsl:if><xsl:if test="(@s = 2) or (@s = 3) or (@s = 6) or (@s = 7)">font-style: italic;</xsl:if><xsl:if test="(@s = 4) or (@s = 5) or (@s = 6) or (@s = 7)">text-decoration: underline;</xsl:if></xsl:attribute>
    <xsl:apply-templates/>
</span>
</xsl:template>

<xsl:template match="c">
<span>
    <xsl:attribute name="style">color:<xsl:value-of select="@v"/></xsl:attribute>
    <xsl:apply-templates/>
</span>
</xsl:template>

<xsl:template match="b">
<span>
    <xsl:attribute name="style">background-color:<xsl:value-of select="@v"/></xsl:attribute>
    <xsl:apply-templates/>
</span>
</xsl:template>

<xsl:template match="a">
<a>
 <xsl:attribute name="href">
  <xsl:value-of select="@h" />
 </xsl:attribute>
 <xsl:value-of select="@h" />
 <xsl:apply-templates/>
</a>
</xsl:template>

<xsl:template match="p">
 <span>
  <xsl:apply-templates />
 </span>
</xsl:template>

<xsl:template match="i[@n='bigsmile']"> :D <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='growl']"> :E <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='mad']"> X( <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='scared']"> :O <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='tongue']"> :p <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='devil']"> }:) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='happy']"> :) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='messed']"> X) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='sidefrown']"> :{ <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='upset']"> B| <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='frazzled']"> :Z <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='heart']"> :X <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='nerd']"> Q) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='sinister']"> :B <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='wink']"> ;-) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='geek']"> B) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='laugh']"> :)) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='oops']"> :G <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='smirk']"> :&apos; <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='worried']"> :[ <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='googles']"> %) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='mohawk']"> -: <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='pirate']">  P) <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='straight']"> :| <xsl:apply-templates /></xsl:template>
<xsl:template match="i[@n='kiss']"> :x <xsl:apply-templates /></xsl:template>

</xsl:stylesheet>
