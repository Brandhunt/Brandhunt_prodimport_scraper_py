#!/usr/bin/env python
# -*- coding: utf-8 -*- 

#  /|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\/|\  
# <   -  Brandhunt Product Import Scraper   -   >
#  \|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/\|/

# --- IMPORT SECTION --- #

import os
os.environ['SCRAPERWIKI_DATABASE_NAME'] = 'sqlite:///data.sqlite'

from datetime import datetime, timedelta
import scraperwiki
from lxml import etree
import lxml.html
import requests
import json
import base64
import mysql.connector
import re
from slugify import slugify
import sys
#import time
import traceback
#from urllib2 import HTTPError
from urllib.error import HTTPError
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

# --- FUNCTION SECTION --- #

# *** --- Replacement for PHP's array merge functionality --- *** #
def array_merge(array1, array2):
    if isinstance(array1, list) and isinstance(array2, list):
        return array1 + array2
    elif isinstance(array1, dict) and isinstance(array2, dict):
        return dict(list(array1.items()) + list(array2.items()))
    elif isinstance(array1, set) and isinstance(array2, set):
        return array1.union(array2)
    return False

# *** --- For checking if a certain product attribute exists --- *** #
def doesprodattrexist(prodattrlist, term, taxonomy):
    for prodattr in prodattrlist:
        if prodattr['term_id'] == term or prodattr['name'] == term or prodattr['slug'] == term:
            return prodattr
    return 0
    
# *** --- For getting proper value from scraped HTML elements --- *** #
def getmoneyfromtext(price):
    val = re.sub(r'\.(?=.*\.)', '', price.replace(',', '.'))
    if not val: return val
    else: return '{:.0f}'.format(float(re.sub(r'[^0-9,.]', '', val)))
    
# *** --- For converting scraped price to correct value according to wanted currency --- *** #
def converttocorrectprice(price, currencysymbol):
    r = requests.get('https://api.exchangeratesapi.io/latest?base=' + currencysymbol + '', headers=headers)
    json = r.json()
    jsonrates = json['rates']
    foundinrates = False
    for ratekey, ratevalue in jsonrates.items():
        if price.find('' + ratekey + '') != -1:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
            #print('CURRENCY: ' + currencysymbol)
            #print('PRICE: ' + price)
            #print('RATEKEY: ' + ratekey)
            #print('RATEVALUE: ' + str(ratevalue))
            price = float(price) / ratevalue
            price = getmoneyfromtext(str(price))
            foundinrates = True
            break
    if not foundinrates:
        if price.find(u'$') != -1:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
            price = float(price) / jsonrates['USD']
            price = getmoneyfromtext(str(price))
        elif price.find(u'£') != -1:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
            price = float(price) / jsonrates['GBP']
            price = getmoneyfromtext(str(price))
        elif price.find(u'€') != -1:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
            price = float(price) / jsonrates['EUR']
            price = getmoneyfromtext(str(price))
        else:
            price = price.replace(r'[^0-9,.]', '')
            price = getmoneyfromtext(price)
    #print("CONVERTEDPRICE:" + price)
    return price

# *** --- For grabbing URLs from text-based values/strings --- *** #
def graburls(text, imageonly):
    try:
        imgsuffix = ''
        if imageonly:
            imgsuffix = '\.(gif|jpg|jpeg|png|svg|webp)'
        else:
            imgsuffix = '\.([a-zA-Z0-9\&\.\/\?\:@\-_=#])*'
        finalmatches = []
        # --> For URLs without URL encoding characters:
        matches = re.finditer(r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:\~@\-_=#]+' + imgsuffix + '', text)
        for match in matches:
            finalmatches.append(match.group())
        #print('URLNOENCODEMATCHES:')
        #for match in matches: print(match)
        # --> For URLs - with - URL encoding characters:
        matches = re.finditer(r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\\%:\~@\-_=#]+' + imgsuffix + '', text)
        for match in matches:
            finalmatches.append(match.group())
        #print('URLNOENCODEMATCHES:')
        #for match in matches: print(match)
        #print('FINALMATCHES')
        #for match in finalmatches: print(match)
        finalmatches = list(set(finalmatches))
        return { i : finalmatches[i] for i in range(0, len(finalmatches)) }
    except:
        print('Error grabbing urls!')
        print(traceback.format_exc())
        return []
    
# *** --- For converting relative URLs to absolute URLs --- *** #
def reltoabs(relurl, baseurl):
    pass
   
# *** --- Check if a certain scraping site already exists --- *** #
# *** --- RETURN: Tuple consiting of (scrapesite, urlTrue_domainFalse) --- *** #
def doesscrapeurlexist(scrapesitelist, scrapeurl):
    scrapesite_domain = ''
    for scrapesite in scrapesitelist:
        if scrapesite['scrapeurl'] == scrapeurl:
            return (scrapesite, True)
        elif scrapesite['scrapeurl']['domain'] == url and scrapesite_domain == '':
            scrapesite_domain = (scrapesite, False)
    return scrapesite_domain if scrapesite_domain != '' else 0

# --> First, check if the database should be reset:

#if bool(os.environ['MORPH_RESET_DB']):
#    if scraperwiki.sql.select('* from data'):
#        scraperwiki.sql.execute('DELETE FROM data')

#from pathlib import Path
#print("File      Path:", Path(__file__).absolute())
#print("Directory Path:", Path().absolute())

# --> Connect to Wordpress Site via REST API and get all the proper URLs to be scraped!

wp_username = os.environ['MORPH_WP_USERNAME']
wp_password = os.environ['MORPH_WP_PASSWORD']
wp_connectwp_url = os.environ['MORPH_WP_CONNECT_URL']
#wp_connectwp_url_2 = os.environ['MORPH_WP_CONNECT_URL_2']
wp_connectwp_url_3 = os.environ['MORPH_WP_CONNECT_URL_3']
#wp_connectwp_url_4 = os.environ['MORPH_WP_CONNECT_URL_4']
#wp_connectwp_url_5 = os.environ['MORPH_WP_CONNECT_URL_5']
wp_connectwp_url_6 = os.environ['MORPH_WP_CONNECT_URL_6']

encodestring = wp_username + ':' + wp_password;
#token = base64.standard_b64encode(wp_username + ':' + wp_password)
token = base64.b64encode(encodestring.encode())
headers = {'Authorization': 'Basic ' + token.decode('ascii')}

offset = int(os.environ['MORPH_PRODIMPURL_OFFSET'])
doesprodexistoffset = int(os.environ['MORPH_PRODCHECK_OFFSET'])
limit = 25

#r = requests.get(wp_connectwp_url + str(offset) + '/' + str(limit) + '/', headers=headers)
r = requests.get(wp_connectwp_url, headers=headers)
jsonscrapsites = json.loads(r.content)

#r = requests.get(wp_connectwp_url_2, headers=headers)
#jsonwebsites = json.loads(r.content)

r = requests.get(wp_connectwp_url_3, headers=headers)
jsonprodattr = json.loads(r.content)

#r = requests.get(wp_connectwp_url_4, headers=headers)
#jsoncatsizetypemaps = json.loads(r.content)

#r = requests.get(wp_connectwp_url_5, headers=headers)
#jsoncatmaps = json.loads(r.content)

r = requests.get(wp_connectwp_url_6 + str(doesprodexistoffset) + '/' + str(limit) + '/', headers=headers)
jsonprodexists = json.loads(r.content)

# --> Decode and handle these product import URLs!
#while jsonscrapsites:
#print(json.dumps(jsonscrapsites))
for scrapsite in jsonscrapsites:
    #print(json.dumps(scrapsite))
    # --> Ignore current product import URL if neccessary!
    if scrapsite['scrapefield']['productignorethisone'] == '1':
        continue
    # --> If scraping a new, unadded scrapesite - Make sure to set default values where neccessary!
    if not scrapsite['scrapefield']['scrapetype']:
        scrapsite['scrapefield']['scrapetype'] = 'standard'
    if not scrapsite['scrapefield']['phantomjsimport']:
        scrapsite['scrapefield']['phantomjsimport'] = 'phantomjsimport_pagenumber'
    # >>> GET THE HTML <<< #
    if scrapsite['scrapefield']['scrapetype'] == 'standard_morph_io':
        html = ''
        root = ''
        nextURLs = ''
        try:
            html = scraperwiki.scrape(scrapsite['scrapeurl'],\
                   user_agent='Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36')
            #print("HTML:")
            #print(html)
        except HTTPError as err:
            if err.code == 302:
                try:
                    url_headers = {'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',\
                    'User-Agent':'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36',\
                              'Accept-Encoding':'gzip, deflate',\
                              'Accept-Language':'en-US,en;q=0.8'}
                    url_session = requests.session()
                    response = url_session.get(url=scrapsite['scrapeurl'], headers=url_headers)
                    html = response.content
                except:
                    print(traceback.format_exc())
            elif err.code == 404:
                notfound = True
                removeon404 = False
                if scrapsite['scrapefield']['domainmisc']:
                    if scrapsite['scrapefield']['domainmisc'].find('allow_remove_on_404'):
                        removeon404 = True
                try:
                    scraperwiki.sqlite.save(unique_keys=['scrapeurl'],\
                                data={'scrapeurl': scrapsite['scrapeurl'],\
                                      'domain': scrapsite['scrapefield']['domain'],\
                                      'domainname': scrapsite['scrapefield']['domainname'],\
                                      'currencysymbol': scrapsite['scrapefield']['currencysymbol'],\
                                      'type': scrapsite['scrapefield']['type'],\
                                      'scrapetype': scrapsite['scrapefield']['scrapetype'],\
                                      'phantomjsimport': scrapsite['scrapefield']['phantomjsimport'],\
                                      'titleselector': scrapsite['scrapefield']['titleselector'],\
                                      'productselector': scrapsite['scrapefield']['productselector'],\
                                      'priceselector': scrapsite['scrapefield']['priceselector'],\
                                      'urlselector': scrapsite['scrapefield']['urlselector'],\
                                      'salespriceselector': scrapsite['scrapefield']['salespriceselector'],\
                                      'imageselector': scrapsite['scrapefield']['imageselector'],\
                                      'productlogoselector': scrapsite['scrapefield']['productlogoselector'],\
                                      'domainmisc': scrapsite['scrapefield']['domainmisc'],\
                                      'productnumberselector': scrapsite['scrapefield']['productnumberselector'],\
                                      'productloadmoreselector': scrapsite['scrapefield']['productloadmoreselector'],\
                                      'productlatestonly': scrapsite['scrapefield']['productlatestonly'],\
                                      'productignorethisone': scrapsite['scrapefield']['productignorethisone'],\
                                      'productnocommaasdelimiter': scrapsite['scrapefield']['productnocommaasdelimiter'],\
                                      'shouldberemoved': removeon404}, table_name = 'urls')
                    #'notfound': notfound,\
                    continue
                except:
                    print(traceback.format_exc())
                    continue
            else:
                raise
        except:
            print(traceback.format_exc())
            #HAPP
        # >>> GET THE HTML ROOT <<< #
        root = lxml.html.fromstring(html)
        #print("ROOT:")
        #for r in root: print r
        # >>> GET THE NEXT URL(S) <<< #
        scrapsite['scrapefield']['productnumberselector'] = scrapsite['scrapefield']['productnumberselector'].encode().decode("unicode-escape")
        if scrapsite['scrapefield']['phantomjsimport'] == 'phantomjsimport_pagenumber':
            url_elements = root.cssselect(scrapsite['scrapefield']['productnumberselector'])
            if url_elements:
                nextURLs = graburls(str(etree.tostring(url_elements[0])), False)
        elif scrapsite['scrapefield']['phantomjsimport'] == 'phantomjsimport_pagenumber_alt':
            url_elements = root.cssselect(scrapsite['scrapefield']['productnumberselector'])
            if url_elements:
                nextURLs = graburls(str(etree.tostring(url_elements[int(int(url_elements.len()) - 1)])), False)
        elif scrapsite['scrapefield']['phantomjsimport'] != 'phantomjsimport_default':
            print("Invalid scraping method - Can't use 'Standard' scraping type with method '" + scrapsite['scrapefield']['phantomjsimport'] + "'!")
            continue
        # >>> HANDLE HTML <<< #
        if html != '' and root != '':
            # --> Go through the "next" URLs - Do they already exists? 
            # --> Regardless, make sure it's added to the current scraping queue if neccessary
            if nextURLs:
                for url in nextURLs:
                    if url:
                        existingurl = doesscrapeurlexist(jsonscrapsites, url)
                        if existingurl != 0:
                            if existingurl[1] is True:
                                continue
                            else:
                                scraperwiki.sqlite.save(unique_keys=['scrapeurl'],\
                                data={'scrapeurl': url,\
                                      'domain': existingurl[0]['scrapefield']['domain'],\
                                      'domainname': existingurl[0]['scrapefield']['domainname'],\
                                      'currencysymbol': existingurl[0]['scrapefield']['currencysymbol'],\
                                      'type': existingurl[0]['scrapefield']['type'],\
                                      'scrapetype': existingurl[0]['scrapefield']['scrapetype'],\
                                      'phantomjsimport': existingurl[0]['scrapefield']['phantomjsimport'],\
                                      'titleselector': existingurl[0]['scrapefield']['titleselector'],\
                                      'productselector': existingurl[0]['scrapefield']['productselector'],\
                                      'priceselector': existingurl[0]['scrapefield']['priceselector'],\
                                      'urlselector': existingurl[0]['scrapefield']['urlselector'],\
                                      'salespriceselector': existingurl[0]['scrapefield']['salespriceselector'],\
                                      'imageselector': existingurl[0]['scrapefield']['imageselector'],\
                                      'productlogoselector': existingurl[0]['scrapefield']['productlogoselector'],\
                                      'domainmisc': existingurl[0]['scrapefield']['domainmisc'],\
                                      'productnumberselector': existingurl[0]['scrapefield']['productnumberselector'],\
                                      'productloadmoreselector': existingurl[0]['scrapefield']['productloadmoreselector'],\
                                      'productlatestonly': existingurl[0]['scrapefield']['productlatestonly'],\
                                      'productignorethisone': existingurl[0]['scrapefield']['productignorethisone'],\
                                      'productnocommaasdelimiter': existingurl[0]['scrapefield']['productnocommaasdelimiter'],\
                                      'shouldberemoved': False}, table_name = 'urls')
                                jsonscrapsites.append({'scrapeurl': url,\
                                      'scrapefield': {\
                                         'domain': existingurl[0]['scrapefield']['domain'],\
                                         'domainname': existingurl[0]['scrapefield']['domainname'],\
                                         'currencysymbol': existingurl[0]['scrapefield']['currencysymbol'],\
                                         'type': existingurl[0]['scrapefield']['type'],\
                                         'scrapetype': existingurl[0]['scrapefield']['scrapetype'],\
                                         'phantomjsimport': existingurl[0]['scrapefield']['phantomjsimport'],\
                                         'titleselector': existingurl[0]['scrapefield']['titleselector'],\
                                         'productselector': existingurl[0]['scrapefield']['productselector'],\
                                         'priceselector': existingurl[0]['scrapefield']['priceselector'],\
                                         'urlselector': existingurl[0]['scrapefield']['urlselector'],\
                                         'salespriceselector': existingurl[0]['scrapefield']['salespriceselector'],\
                                         'imageselector': existingurl[0]['scrapefield']['imageselector'],\
                                         'productlogoselector': existingurl[0]['scrapefield']['productlogoselector'],\
                                         'domainmisc': existingurl[0]['scrapefield']['domainmisc'],\
                                         'productnumberselector': existingurl[0]['scrapefield']['productnumberselector'],\
                                         'productloadmoreselector': existingurl[0]['scrapefield']['productloadmoreselector'],\
                                         'productlatestonly': existingurl[0]['scrapefield']['productlatestonly'],\
                                         'productignorethisone': existingurl[0]['scrapefield']['productignorethisone'],\
                                         'productnocommaasdelimiter': existingurl[0]['scrapefield']['productnocommaasdelimiter']}})
                        else:
                            print('Current URL "' + url + '" is not of the current domain or scraping URL - It will be skipped!')
                            continue
                    else:
                        print('FOUND THE END OF THE NEXT URL!')
            print("Currently scraping URL " + str(scrapsite['scrapeurl']))
            # >>> GET THE PRODUCTS <<< #
            scrapsite['scrapefield']['productselector'] = scrapsite['scrapefield']['productselector'].encode().decode("unicode-escape")
            product_elements = root.cssselect(scrapsite['scrapefield']['productselector'])
            for prod_el in product_elements:
                if prod_el is not None:
                    prod_html = etree.tostring(prod_el)
                    prod_root = lxml.html.fromstring(prod_html)
                    prod_sold_out = False
                    # >>> GET THE SCRAPED PRODUCT URL <<< #
                    prod_url = ''
                    prod_url_html = ''
                    try:
                        scrapsite['scrapefield']['urlselector'] = scrapsite['scrapefield']['urlselector'].encode().decode("unicode-escape")
                        product_urL_element = prod_root.cssselect(scrapsite['scrapefield']['urlselector'])[0]
                        if product_urL_element is not None:
                            prod_url_html = str(etree.tostring(product_urL_element))
                            matches = re.search(r'https?:\/\/(?![^" ]*(?:gif|jpg|jpeg|png|svg))[^" ]+', prod_url_html)
                            if matches:
                                prod_url = matches[0]
                            if prod_url is None or prod_url == '':
                                #print(prod_url_html)
                                #matches = re.search(r'href\=\"\K(.*?)\"', prod_url_html)
                                matches = re.search(r'href\=\"(.*?)\"', prod_url_html)
                                prod_url = matches[1]
                                new_prod_url = urljoin(scrapsite['scrapeurl'], prod_url)
                                if prod_url != new_prod_url:
                                    prod_url = new_prod_url
                                if prod_url.find('//') == -1:
                                    print('Absolute product URL could not be created out of relative URL!')
                                    continue
                                if prod_url[0:2] == '//':
                                    prod_url = 'https:' + prod_url
                        else:
                            print('No product URL found. Either broken config or headless browser setup needs change')
                    except:
                        print(traceback.format_exc())
                    # >>> GET THE SCRAPED PRODUCT TITLE <<< #
                    prod_title = ''
                    try:
                        scrapsite['scrapefield']['titleselector'] = scrapsite['scrapefield']['titleselector'].encode().decode("unicode-escape")
                        if scrapsite['scrapefield']['titleselector'].find('[multiple],') != -1:
                            scrapsite['scrapefield']['titleselector'].replace('[multiple],', '')
                            producttitleparts = prod_root.cssselect(scrapsite['scrapefield']['titleselector'])
                            for el in producttitleparts:
                                if el is None:
                                    continue
                                if el.text is None:
                                    continue
                                prod_title = prod_title + el.text + ' '
                        else:
                            title = prod_root.cssselect(scrapsite['scrapefield']['titleselector'])[0].text
                            if title is not None:
                                prod_title = title
                        if prod_title.strip() == '':
                            print('Cannot find the product title after trimming!')
                        else:
                            prod_title = re.sub('\s+', ' ', prod_title)
                    except:
                        print(traceback.format_exc())
                    # >>> CHECK IF LATEST ONLY <<< #
                    # --> If the url should be checked for the latest products only(No full import),
                    # --> then make sure to stop importing the products from the current URL when
                    # --> we come across a product not previously stored in the database!
                    if scrapsite['scrapefield']['productlatestonly'] == '1':
                        existingtable = scraperwiki.sql.table_info('exisprodcache')
                        if not existingtable:
                            while jsonprodexists:
                                count = 1
                                while count <= jsonprodexists.len():
                                    scraperwiki.sqlite.save(unique_keys=['count'],\
                                        data = {'count': ((count - 1) + doesprodexistoffset),\
                                        'prodexcerpt': jsonprodexists[count],\
                                              'date': jsonprodexists[0]}, table_name = 'exisprodcache')
                                    count = count + 1
                                doesprodexistoffset = doesprodexistoffset + limit
                                r = requests.get(wp_connectwp_url_6 + str(doesprodexistoffset) + '/' + str(limit) + '/', headers=headers)
                                jsonprodexists = json.loads(r.content)
                        else:
                            db_date = list(scraperwiki.sql.select('date FROM exisprodcache ORDER BY CAST(date AS INT) ASC LIMIT 1'))[0]
                            db_date = datetime(year=int(db_date[0:4]),\
                                               month=int(db_date[4:6]),\
                                               day=int(db_date[6:8]),\
                                               hour=int(db_date[8:10]),\
                                               minute=int(db_date[10:12]),\
                                               second=int(db_date[12:14]))
                            current_date = (datetime.utcnow() + timedelta(seconds=60*60))
                            duration = (current_date - db_date).total_seconds()
                            hour_diff = divmod(duration, 3600)[0]
                            if (hour_diff > 24):
                                while jsonprodexists:
                                    count = 1
                                    while count <= jsonprodexists.len():
                                        scraperwiki.sqlite.save(unique_keys=['count'],\
                                            data = {'count': ((count - 1) + doesprodexistoffset),\
                                            'prodexcerpt': jsonprodexists[count],\
                                                  'date': jsonprodexists[0]}, table_name = 'exisprodcache')
                                        count = count + 1
                                    doesprodexistoffset = doesprodexistoffset + limit
                                    r = requests.get(wp_connectwp_url_6 + str(doesprodexistoffset) + '/' + str(limit) + '/', headers=headers)
                                    jsonprodexists = json.loads(r.content)
                        product_search_result = scraperwiki.sql.select('* FROM exisprodcache WHERE prodexcerpt REGEXP ' + scrapsite['scrapefield'] + '')   
                        if product_search_result:
                            print("Found product already existing, moving onto next product!");
                            continue
                    # >>> GET THE PRICE <<< #
                    prod_price_elements = ''
                    prod_price = ''
                    try:
                        scrapsite['scrapefield']['priceselector'] = scrapsite['scrapefield']['priceselector'].encode().decode("unicode-escape")
                        #print(scrapsite['scrapefield']['priceselector'])
                        if scrapsite['scrapefield']['priceselector'].find('[multiple],') != -1:
                            scrapsite['scrapefield']['priceselector'].replace('[multiple],', '')
                            prod_price_elements = prod_root.cssselect(scrapsite['scrapefield']['priceselector'])
                            for el in prod_price_elements:
                                if el is None:
                                    continue
                                prod_price = prod_price + el.text + ' '
                            if prod_price != '':
                                prod_price = re.sub(r'([^a-zA-Z]\w+\%+)', '', prod_price)
                        else:
                            prod_price_elements = prod_root.cssselect(scrapsite['scrapefield']['priceselector'])
                            if prod_price_elements:
                                for price_el in prod_price_elements:
                                    if price_el.text is not None:
                                        if any(char.isdigit() for char in price_el.text):
                                            prod_price = price_el.text
                                            prod_price = re.sub(r'([^a-zA-Z]\w+\%+)', '', prod_price)
                                            break
                                        else:
                                            prod_price = '-1'
                            else:
                                prod_price = '-1'
                        if re.search('Sold\s*Out', prod_price, flags=re.IGNORECASE):
                            prod_price = '0 ' + scrapsite['scrapefield']['currencysymbol'] + ''
                            prod_sold_out = True
                        elif scrapsite['scrapefield']['productnocommaasdelimiter'] == '1':
                            prod_price = prod_price.replace('\,', '')
                        #print('FINALPRICE:' + prod_price)
                    except:
                        print(traceback.format_exc())
                    # >>> GET THE SALES PRICE <<< #
                    prod_salesprice_elements = ''
                    prod_salesprice = ''
                    if scrapsite['scrapefield']['salespriceselector']:
                        try:
                            scrapsite['scrapefield']['salespriceselector'] = scrapsite['scrapefield']['salespriceselector'].encode().decode("unicode-escape")
                            prod_salesprice_elements = prod_root.cssselect(scrapsite['scrapefield']['salespriceselector'])   
                            if prod_salesprice_elements:
                                if any(char.isdigit() for char in prod_salesprice_elements[0].text):
                                    prod_salesprice = prod_salesprice_elements[0].text
                                    prod_salesprice = re.sub(r'([^a-zA-Z]\w+\%+)', '', prod_salesprice)
                                else:
                                    prod_salesprice = '-1'
                            else:
                                prod_salesprice = '-1'
                            if re.search('Sold\s*Out', prod_salesprice, flags=re.IGNORECASE):
                                prod_salesprice = '0 ' + scrapsite['scrapefield']['currencysymbol'] + ''
                                prod_sold_out = True
                            elif scrapsite['scrapefield']['productnocommaasdelimiter'] == '1':
                                prod_salesprice = prod_salesprice.replace('\,', '')
                        except:
                            print(traceback.format_exc())
                    # >>> CHECK IF BRAND IS FOUND IN NAME <<< #
                    prod_brand = ''
                    try:
                        brand_terms = jsonprodattr['pa_brand']
                        for brandterm in brand_terms:
                            brandus = brandterm['name'].lower()
                            titlus = prod_title.lower()
                            if re.search(r'' + brandus + '', titlus) is not None:
                                prod_brand = brandterm['name']
                                break
                    except:
                        print(traceback.format_exc())            
                    # >>> CHECK IF DOMAIN NAME SHOULD BE USED AS PROD. BRAND <<< #
                    if scrapsite['scrapefield']['domainname']:
                        try:
                            if prod_brand == '':
                                prod_brand = scrapsite['scrapefield']['domainname']
                        except:
                            print(traceback.format_exc())
                    # >>> GET THE DOMAIN MISC. ELEMENTS <<< #
                    domainmisc_array = ''
                    # --> Define containers for product attributes
                    prod_colors = ''
                    prod_sizes = ''
                    prod_categories = ''
                    # --> Define values that will be saved to database once done:
                    sizetypemisc = ''
                    preexistingcurrency = ''
                    altimggrab = ''
                    ignoreurlscontainingstring = ''
                    femaletruemalefalse = ''
                    soldout = False
                    scrapedmiscitems = ''
                    # --> Get 'em!
                    if scrapsite['scrapefield']['domainmisc']:
                        try:
                            domainmisc_array = re.split('{|}', scrapsite['scrapefield']['domainmisc'])
                            for i in range(2, len(domainmisc_array), 2):
                                #domainmisc_array[i] = prod_root.cssselect(domainmisc_array[i])
                                # --- Are the sizes belonging to the current product of a a specific misc. size type? --- #
                                if domainmisc_array[(i-1)] == 'sizetypemisc':
                                    sizetypemisc = domainmisc_array[i]
                                # --- Are there any pre-existing currencies to apply to the price(s)? --- #
                                if domainmisc_array[(i-1)] == 'pre_existing_currency':
                                    preexistingcurrency = domainmisc_array[i]
                                    prod_price = prod_price + domainmisc_array[i].strip()
                                    if prod_salesprice != '':
                                        prod_salesprice = prod_salesprice + domainmisc_array[i].strip()
                                # --- Any alternative ways to utilize for grabbing image urls? --- #
                                if domainmisc_array[(i-1)] == 'alt_img_grab':
                                    altimggrab = '1'
                                if domainmisc_array[(i-1)] == 'alt_img_grab_2':
                                    altimggrab = '2'
                                # --- Should the product skip any URLs(Product logo and normal IMGs) containing any specific string(s)? --- #
                                if domainmisc_array[(i-1)] == 'skip_img_containing':
                                    ignoreurlscontainingstring = domainmisc_array[i]
                                # --- Should the product apply a specific category automatically? --- #
                                if domainmisc_array[(i-1)] == 'add_category':
                                   prod_categories = ','.split(domainmisc_array[i])
                                # --- Should the product apply the male/female attribute automatically? --- #
                                if domainmisc_array[(i-1)] == 'is_male':
                                    femaletruemalefalse = 'M'
                                elif domainmisc_array[(i-1)] == 'is_female':
                                    femaletruemalefalse = 'F'
                                # --> Attempt scraping of product misc. elements:
                                #if domainmisc_array[(i-1)] == 'pa_size':
                                #    print('TOSCRAPE: ' + domainmisc_array[i].strip().encode().decode("unicode-escape"))
                                #    print(prod_html)
                                domainmisc_array[i] = prod_root.cssselect(domainmisc_array[i].strip().encode().decode("unicode-escape"))
                                if domainmisc_array[i]:
                                    # --- Has the product got any special sale price applied? --- #
                                    if domainmisc_array[(i-1)] == 'before_sale_price':
                                        if len(domainmisc_array[i]) > 0:
                                            newprice = domainmisc_array[i][0].text
                                            prod_salesprice = prod_price
                                            prod_price = newprice
                                            if preexistingcurrency != '':
                                                prod_price = prod_price + preexistingcurrency.strip()
                                    # --- Apply brand, color, category and size
                                    if domainmisc_array[(i-1)] == 'pa_brand':
                                        if len(domainmisc_array[i]) > 0:
                                            prod_brand = domainmisc_array[i][0].text
                                    if domainmisc_array[(i-1)] == 'pa_color':
                                        if len(domainmisc_array[i]) > 0:
                                            count = 0
                                            prod_colors = []
                                            for el in domainmisc_array[i]:  
                                                prod_colors.append(domainmisc_array[i][count].text)
                                                count = count + 1
                                    if domainmisc_array[(i-1)] == 'pa_category':
                                        if len(domainmisc_array[i]) > 0:
                                            prodcat_array = []
                                            count = 0
                                            for el in domainmisc_array[i]:  
                                                prodcat_array.append(domainmisc_array[i][count].text)
                                                count = count + 1
                                            if prod_categories != '':
                                                prod_categories = [prod_categories, prodcat_array]
                                            else:
                                                prod_categories = prodcat_array
                                    if domainmisc_array[(i-1)] == 'pa_size':
                                        #print(prod_html)
                                        #print(domainmisc_array[i])
                                        if len(domainmisc_array[i]) > 0:
                                            count = 0
                                            for el in domainmisc_array[i]:
                                                #print(el.text)
                                                #print(domainmisc_array[i][count].text)
                                                prod_sizes.append(domainmisc_array[i][count].text)
                                                count = count + 1
                                    # --- Should we skip the first size alternative on information import? --- #
                                    if domainmisc_array[(i-1)] == 'skip_first_size':
                                        if prod_sizes != '':
                                            removed_size = prod_sizes.pop(0)
                                    # --- Has the product sold out yet? --- #
                                    if domainmisc_array[(i-1)] == 'sold_out':
                                        if len(domainmisc_array[i]) > 0:
                                            soldout = True
                                    # --- Convert the scraped HTML element to HTML string before end! --- #
                                    if type(domainmisc_array[i]) is list:
                                        count = 0
                                        for el in domainmisc_array[i]:
                                            domainmisc_array[i][count] = str(etree.tostring(el))
                                            count = count + 1
                                    else:
                                        domainmisc_array[i] = str(etree.tostring(domainmisc_array[i]))
                            scrapedmiscitems = json.dumps(domainmisc_array)
                            #print('DOMAINMISC:')
                            #for d in domainmisc_array: print d
                        except:
                            print(traceback.format_exc())
                    # >>> GET THE PRODUCT LOGO URL(S) - IF SUCH EXISTS <<< #
                    prodlog_image_urls = ''
                    productlogourls = ''
                    if scrapsite['scrapefield']['productlogoselector']:
                        try:
                            scrapsite['scrapefield']['productlogoselector'] = scrapsite['scrapefield']['productlogoselector'].encode().decode("unicode-escape")
                            prodlog_image_elements = prod_root.cssselect(scrapsite['scrapefield']['productlogoselector'])
                            if prodlog_image_elements:
                                for i in range(len(prodlog_image_elements)):
                                    prodlog_image_elements[i] = etree.tostring(prodlog_image_elements[i])
                                image_dom = ','.join(prodlog_image_elements)
                                if altimggrab == '1':
                                    #output = re.search(r'image\=\"(.*)\"', image_dom, flags=re.U)
                                    output = re.search(r'image\=\"(.*?)\"', image_dom)
                                    if len(output.group(1)) > 0:
                                        prodlog_image_urls = { 0 : output.group(1) }
                                    #if output.len() > 0:
                                    #    removed_top_element = output.pop(0)
                                    #    prodlog_image_urls = output
                                elif altimggrab == '2':
                                    #output = re.search(r'src\=\"(.*)\"', image_dom, flags=re.U)
                                    output = re.search(r'src\=\"(.*?)\"', image_dom)
                                    if len(output.group(1)) > 0:
                                        prodlog_image_urls = { 0 : output.group(1) }
                                    #if output.len() > 0:
                                    #    removed_top_element = output.pop(0)
                                    #    prodlog_image_urls = output
                                else:
                                    prodlog_image_urls = graburls(str(image_dom), True)
                                if len(prodlog_image_urls) > 0:
                                    for imagekey, imageval in prodlog_image_urls.copy().items():
                                        newimageval = urljoin(scrapsite['scrapeurl'], imageval)
                                        if imageval != newimageval:
                                            prodlog_image_urls[imagekey] = newimageval
                                            imageval = newimageval
                                        if imageval.find('//') == -1:
                                            del prodlog_image_urls[imagekey]
                                            continue
                                        if imageval.find('blank.') != -1:
                                            del prodlog_image_urls[imagekey]
                                            continue
                                        if imageval[0:2] == '//':
                                            imageval = 'https:' + imageval
                                            prodlog_image_urls[imagekey] = imageval
                                productlogourls = prodlog_image_urls
                            else:
                                print("No product logo URLs could be found for product with title " + prod_title + "!")
                            #print('PRODUCTLOGOS:')
                            #for p in prodlog_image_urls: print(p)
                            #print('PRODUCTLOGOURL:' + productlogourl)
                        except:
                            print(traceback.format_exc())
                    # >>> GET THE IMAGE URL(S) <<< #
                    image_urls = ''
                    image_elements = ''
                    image_urls_valid = ''
                    images = ''
                    if scrapsite['scrapefield']['imageselector'] and len(scrapsite['scrapefield']['imageselector']):
                        try:
                            scrapsite['scrapefield']['imageselector'] = scrapsite['scrapefield']['imageselector'].encode().decode("unicode-escape")
                            #image_urls = ''
                            image_elements = prod_root.cssselect(scrapsite['scrapefield']['imageselector'])
                            #for i in image_elements: print(i)
                            if image_elements:
                                for i in range(len(image_elements)):
                                    image_elements[i] = str(etree.tostring(image_elements[i]))
                                image_dom = ','.join(image_elements)
                                #print('IMAGE DOM: ' + image_dom)
                                if altimggrab == '1':
                                    #output = re.finditer(r'image\=\"(.*)\"', image_dom, flags=re.U)
                                    output = re.finditer(r'image\=\"(.*?)\"', image_dom)
                                    array_output = []
                                    for output_el in output:
                                        #print(output_el.group(1))
                                        array_output.append(output_el.group(1))
                                    if len(array_output) > 0:
                                        #removed_top_element = output.pop(0)
                                        image_urls = { i : array_output[i] for i in range(0, len(array_output)) }
                                elif altimggrab == '2':
                                    #output = re.search(r'src\=\"(.*)\"', image_dom, flags=re.U)
                                    output = re.search(r'src\=\"(.*?)\"', image_dom)
                                    if len(output.group(1)) > 0:
                                        image_urls = { 0 : output.group(1) }
                                    #if len(output.group()) > 0:
                                    #    group = output.group()
                                    #    removed_top_element = group.pop(0)
                                    #    image_urls = group
                                else:
                                    image_urls = graburls(str(image_dom), True)
                                #print('PRE-IMAGE URLS: ')
                                #for img in image_urls: print(image_urls[img])
                            if len(image_urls) > 0:
                                for imagekey, imageval in image_urls.copy().items():
                                    newimageval = urljoin(scrapsite['scrapeurl'], imageval)
                                    #print('NEWIMGVAL: ' + newimageval)
                                    if imageval != newimageval:
                                        image_urls[imagekey] = newimageval
                                        imageval = newimageval
                                    if imageval.find('//') == -1:
                                        #print('HERE')
                                        del prodlog_image_urls[imagekey]
                                        continue
                                    if imageval.find('blank.') != -1:
                                        #print(imageval)
                                        #print(imageval.find('blank.'))
                                        #print('THERE')
                                        del image_urls[imagekey]
                                        continue
                                    if ignoreurlscontainingstring != '':                                
                                        if imageval.find(ignoreurlscontainingstring) != -1:
                                            #print('BUT NOT HERE')
                                            del image_urls[imagekey]
                                            continue
                                    if imageval[0:2] == '//':
                                        imageval = 'https:' + imageval
                                        image_urls[imagekey] = imageval
                                image_urls_valid = list(image_urls.values())
                            #print('IMAGE ELEMENTS:')
                            #for img in image_elements: print (img)
                            #print('IMAGE URLS:')
                            #for img in image_urls: print (img)
                            #print('VALID IMAGES:')
                            #for img in image_urls_valid: print (img)
                        except:
                            print(traceback.format_exc())
                    #MAYBE GET NEWDOMAIN HERE?
                    scraperwiki.sqlite.save(unique_keys=['producturl'],\
                                            data={'domain': scrapsite['scrapefield']['domain'],\
                                                  'scrapeurl': scrapsite['scrapeurl'],\
                                                  'producturl': prod_url,\
                                                  'currencysymbol': scrapsite['scrapefield']['currencysymbol'],\
                                                  'title': prod_title,\
                                                  'price': prod_price,\
                                                  'salesprice': prod_salesprice,\
                                                  'brand': prod_brand,\
                                                  'color': json.dumps(prod_colors),\
                                                  'size': json.dumps(prod_sizes),\
                                                  'sizetypemisc': sizetypemisc,\
                                                  'category': json.dumps(prod_categories),\
                                                  'sex': femaletruemalefalse,\
                                                  'soldout': soldout,\
                                                  'imageurls': json.dumps(image_urls_valid),\
                                                  'logoimageurls': json.dumps(productlogourls),\
                                                  'miscdetails': scrapedmiscitems}, table_name = 'prodstocreate')        
        else:
            continue
    else:
        continue
#offset = offset + limit
#r = requests.get(wp_connectwp_url + str(offset) + '/' + str(limit) + '/', headers=headers)
#jsonscrapsites = r.json()
