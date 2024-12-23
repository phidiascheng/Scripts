import tkinter as tk 
import re
import argparse
import hashlib
import os

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()

class SciHub(object):

    def __init__(self):
        self.sess = requests.Session()
        self.sess.headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:27.0) Gecko/20100101 Firefox/27.0'} #HEADERS
        self.available_base_url_list = self._get_available_scihub_urls()
        self.base_url = self.available_base_url_list[0] + '/'

    def _get_available_scihub_urls(self):
        urls = []
        res = requests.get('https://sci-hub.now.sh/')
        s = self._get_soup(res.content)
        for a in s.find_all('a', href=True):
            if 'sci-hub.' in a['href']:
                urls.append(a['href'])
        return urls

    def _change_base_url(self):
        if not self.available_base_url_list:
            raise Exception('Ran out of valid sci-hub urls')
        del self.available_base_url_list[0]
        self.base_url = self.available_base_url_list[0] + '/'

    def download(self, identifier, destination='', path=None):
        data = self.fetch(identifier)
        if not 'err' in data:
            self._save(data['pdf'],
                       os.path.join(destination, path if path else data['name']))
        return data

    def fetch(self, identifier):
        try:
            url = self._get_direct_url(identifier)
            res = self.sess.get(url, verify=False)
            if res.headers['Content-Type'] != 'application/pdf':
                self._change_base_url()
                raise CaptchaNeedException('Failed to fetch pdf with identifier %s '
                                           '(resolved url %s) due to captcha' % (identifier, url))
            else:
                return {
                    'pdf': res.content,
                    'url': url,
                    'name': self._generate_name(res)
                }
        except requests.exceptions.ConnectionError:
            self._change_base_url()
        except requests.exceptions.RequestException as e:
            return {
                'err': 'Failed to fetch pdf with identifier %s (resolved url %s) due to request exception.'
                       % (identifier, url)
            }

    def _get_direct_url(self, identifier):
        id_type = self._classify(identifier)
        return identifier if id_type == 'url-direct' \
            else self._search_direct_url(identifier)

    def _search_direct_url(self, identifier):
        res = self.sess.get(self.base_url + identifier, verify=False)
        s = self._get_soup(res.content)
        iframe = s.find('iframe')
        if iframe:
            return iframe.get('src') if not iframe.get('src').startswith('//') \
                else 'http:' + iframe.get('src')

    def _classify(self, identifier):
        if (identifier.startswith('http') or identifier.startswith('https')):
            if identifier.endswith('pdf'):
                return 'url-direct'
            else:
                return 'url-non-direct'
        elif identifier.isdigit():
            return 'pmid'
        else:
            return 'doi'

    def _save(self, data, path):
    	with open(path, 'wb') as f:
    		f.write(data)

    def _get_soup(self, html):
        return BeautifulSoup(html, 'html.parser')

    def _generate_name(self, res):
        name = res.url.split('/')[-1]
        name = re.sub('#view=(.+)', '', name)
        pdf_hash = hashlib.md5(res.content).hexdigest()
        return '%s-%s' % (pdf_hash, name[-20:])

class CaptchaNeedException(Exception):
    pass



window = tk.Tk()
window.title('SciHub下载器')

DoiBox = tk.StringVar()
LinkBox = tk.StringVar()
PubMedBox = tk.StringVar()
LocationBox = tk.StringVar()
FileNameBox = tk.StringVar()

tk.Label(window,text='请先使用标题搜索确定填写以下信息中的至少一项，目录留空默认保存到下载根文件夹').grid(row=0,columnspan=2,sticky='w')
tk.Label(window,text='DOI号: ').grid(row=1,column=0,sticky='e')
tk.Entry(window,show=None,textvariable=DoiBox,width=70).grid(row=1,column=1,sticky='w')
tk.Label(window,text='官网地址: ').grid(row=3,column=0,sticky='e')
tk.Entry(window,show=None,textvariable=LinkBox,width=70).grid(row=3,column=1,sticky='w')
tk.Label(window,text='PubMed号: ').grid(row=2,column=0,sticky='e')
tk.Entry(window,show=None,textvariable=PubMedBox,width=70).grid(row=2,column=1,sticky='w')
tk.Label(window,text='文件夹/：').grid(row=4,column=0,sticky='e')
tk.Entry(window,show=None,textvariable=LocationBox,width=70).grid(row=4,column=1,sticky='w')
tk.Label(window,text='文件名/：').grid(row=5,column=0,sticky='e')
tk.Entry(window,show=None,textvariable=FileNameBox,width=70).grid(row=5,column=1,sticky='w')


def DownLoadProcess():
	ID = [DoiBox.get(), PubMedBox.get(), LinkBox.get() ]
	Location = os.environ['HOME']+"/Downloads/"+LocationBox.get()
	if not os.path.exists(Location):
		os.mkdir(Location)
	FileName = FileNameBox.get()
	successORnot = 0

	sh = SciHub()

	for i in ID:
		if i != '':
			if FileName != '':
				FileName = FileName + '.pdf'
			result = sh.download(i, Location, FileName)
			if 'err' not in result:
				output.insert('end','\n下载成功！')
				successORnot = 1
				break
			else:
				output.insert('end','\n'+result['err'])
				output.insert('end','\n再试一次')
	if successORnot == 0:
		output.insert('end','\n对不起，所提供的所有信息都无法下载')



tk.Button(window, text='开始下载', command=DownLoadProcess).grid(row=6,column=0,columnspan=2)
output = tk.Text(window,width=90,height=6)
output.grid(row=7,columnspan=2)

window.mainloop()