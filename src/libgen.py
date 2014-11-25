#!/usr/bin/python
# encoding: utf-8
from __future__ import unicode_literals

import sys
import urllib
from workflow import Workflow, web
from collections import OrderedDict
from bs4 import BeautifulSoup, SoupStrainer

def unify(obj, encoding='utf-8'):
    """Detects if object is a string and if so converts to unicode"""
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj

def check_query(wf):
    """waits for user to end query with '.' before actually initiating search"""

    # get query from user
    query = wf.args[1]

    if query[-1] != '.':
        wf.add_item("Error!", 
                    "Need add '.' after query to execute search", 
                    icon="icons/n_delay.png")
        wf.send_feedback()
        return False
    else:
        return query[:-1]


def _search_libgen(query,pg):
    """Search LibGen for `query`."""
    base_url = "http://gen.lib.rus.ec/search.php?req="
    html_query = urllib.quote(unify(query).encode('utf-8'))
    end ='&phrase=1&view=simple&column=def&sort=title&sortmode=ASC&page='+str(pg)
    libgen_url = base_url + html_query+end
    req = web.get(libgen_url)
    req.raise_for_status()
    return req.text

def parse_libgen(results):
    """Parse LibGen's search results HTML.
    """

    # Extract the relevant result column names
    keys = [s.text.strip().lower()
            for item in results[0:1]
            for s in item.find_all('td')]
    keys = keys[:10]

    # Generate array of dicts for the results
    items = []
    for item in results[1:]: # for each row
        dct = OrderedDict()
        for idx, element in enumerate(item.find_all('td')): # for each column
            if idx < 9: # if relevant column
                key = keys[idx]
                value = element.text
                if idx == 2: # if `Title` column
                    # Get unique hash for each item
                    link = element.a['href']
                    hash_link = link.replace('book/index.php?', '')
                    dct.update({'hash': hash_link})

                    # remove possible ISBNs
                    extras = [s.text for s in element.find_all('font')
                                if '[' not in s.text] # ISBNs
                    if extras != []:
                        for non in extras:
                            value = element.text.replace(non, '')
                if value == '':
                    value = None
                dct.update({key: value})
        items.append(dct)
      

    return items

def prepare_feedback(wf, items):
    """Prepare Alfred results of query.
    """
    if items != []:
        for item in items:
            arg = item['hash'] or ""
            title = item['title'] or ""
            creators = item['author(s)'] or ""
            year = item['year'] or ""
            pages = ""
            if item['pages']:
                pages = item['pages'] + ' pages'
            size = item['size'] or ""
            pre_sub = ' '.join([creators, year])
            post_sub = '; '.join([pages, size])
            sub = pre_sub + ' (' + post_sub + ')'
            
            wf.add_item(title,
                        sub,
                        valid=True,
                        arg=arg)
        return True
    else:
        wf.add_item("Error!", "No results found.", 
                    icon="icons/n_error.png")
        wf.send_feedback()

    

def search(wf, query,pg):
    """Search LibGen for `query`.
    """

    def search_libgen():
        """Wrapper for LibGen search."""
        return _search_libgen(query,pg)

    #Get previous results or do new search
    html = wf.cached_data(query, search_libgen, max_age=604800)
#    html = search_libgen
#    search_libgen()
    # Soupify the HTML results
    res_table = SoupStrainer('table', {"class" : "c"})
    soup = BeautifulSoup(html, parse_only=res_table)
    ind_results = soup.find_all('tr', {"valign" : "top"})
    
    # Parse the results HTML page
    items = parse_libgen(ind_results)

    # Cache the parsed results and send to Alfred
#    wf.cache_data('results', items)
#    prepare_feedback(wf, items)
#    wf.send_feedback()
    return items

def download(hash_link):
    """Dowload the selected item.
    """
    base_url = 'http://gen.lib.rus.ec/get?'
    download_url = base_url + hash_link
    return download_url




def main(wf):
    f = open('results.csv','w')
    if check_query(wf):
        if wf.args[0] == 'search':
            for pg in range(1,50):
                dic = search(wf, wf.args[1],pg)
                for i in dic:
                    try:
                        cont = '\n'+i['id']+','+i['title']+'\n'
                        
                        lis=i['hash'].split('=')
                        cont += str(lis[0])+','+str(lis[1])+'\n'
                        cont +=  i['author(s)']+','+i['pages']+','+i['extension']+','+i['language']+'\n'
#                        's'.split('=')
                        f.write(cont)
                    except:
                        pass
#        print i.keys()
                    print '\n'
                    print i['id'],i['title']
                    print i['author(s)']
                    print i['hash']
        elif wf.args[0] == 'download':
            print  download(wf.args[1])
        else:
            pass
    f.close()


    

if __name__ == '__main__':
    sys.argv[1:4] =['search',' harp.']
    WF = Workflow()
    sys.exit(WF.run(main))
