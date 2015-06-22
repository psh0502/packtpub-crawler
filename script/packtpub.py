import urllib
import requests
from utils import make_soup, wait, download_file
from logs import *

class Packpub(object):
    """
    """

    def __init__(self, config, dev):
        self.__config = config
        self.__dev = dev
        self.__delay = float(self.__config.get('delay', 'delay.requests'))
        self.__url_base = self.__config.get('url', 'url.base')
        self.__headers = self.__init_headers()
        self.__session = requests.Session()
        self.info = {}

    def __init_headers(self):
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
        }

    def __log_response(self, response, method='GET', detail=False):
        print '[-] {0} {1} | {2}'.format(method, response.url, response.status_code)
        if detail:
            print '[-] cookies:'
            log_dict(requests.utils.dict_from_cookiejar(self.__session.cookies))
            print '[-] headers:'
            log_dict(response.headers)

    def __GET_login(self):
        url = self.__url_base
        if self.__dev:
            url += self.__config.get('url', 'url.loginGet')
        else:
            url += self.__config.get('url', 'url.login')

        response = self.__session.get(url, headers=self.__headers)
        self.__log_response(response)

        soup = make_soup(response)
        form = soup.find('form', {'id': 'packt-user-login-form'})
        self.info['form_build_id'] = form.find('input', attrs={'name': 'form_build_id'})['value']
        self.info['form_id'] = form.find('input', attrs={'name': 'form_id'})['value']
        wait(self.__delay)

    def __POST_login(self):
        data = self.info.copy()
        data['email'] = self.__config.get('credential', 'credential.email')
        data['password'] = self.__config.get('credential', 'credential.password')
        data['op'] = 'Login'
        #print '[-] data: {0}'.format(urllib.urlencode(data))

        url = self.__url_base
        response = None
        if self.__dev:
            url += self.__config.get('url', 'url.loginPost')
            response = self.__session.get(url, headers=self.__headers, data=data)
        else:
            url += self.__config.get('url', 'url.login')
            response = self.__session.post(url, headers=self.__headers, data=data)

        self.__log_response(response, 'POST', True)

        soup = make_soup(response)
        div_target = soup.find('div', {'id': 'deal-of-the-day'})

        self.info['title'] = div_target.select('div.dotd-title > h2')[0].string.strip()
        self.info['description'] = div_target.select('div.dotd-main-book-summary > div')[2].string.strip()
        self.info['url_image'] = div_target.select('div.dotd-main-book-image img')[0]['src'].lstrip('//')
        self.info['url_claim'] = self.__url_base + div_target.select('a.twelve-days-claim')[0]['href']
        # remove useless info
        self.info.pop('form_build_id', None)
        self.info.pop('form_id', None)
        wait(self.__delay)

    def __GET_claim(self):
        url = ''
        if self.__dev:
            url = self.__url_base + self.__config.get('url', 'url.account')
        else:
            url = self.info['url_claim']

        response = self.__session.get(url, headers=self.__headers)
        self.__log_response(response)

        soup = make_soup(response)
        div_target = soup.find('div', {'id': 'product-account-list'})

        # only last one just claimed
        self.info['book_id'] = div_target.select('.product-line')[0]['nid']
        self.info['author'] = div_target.find(class_='author').text.strip()
        wait(self.__delay)

    def download_ebooks(self, types):

        self.__GET_login()
        self.__POST_login()
        self.__GET_claim()

        log_json(self.info)

        download_urls = [dict(type=type, \
            url=self.__url_base + self.__config.get('url', 'url.download').format(self.info['book_id'], type), \
            filename=self.info['title'].encode('ascii', 'ignore').replace(' ', '_') + '.' + type) \
            for type in types]

        directory = self.__config.get('path', 'path.ebooks')
        for download in download_urls:
            download_file(self.__session, download['url'], directory, download['filename'])