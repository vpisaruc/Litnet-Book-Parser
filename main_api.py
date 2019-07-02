import requests
from bs4 import BeautifulSoup
import re
from time import sleep
import json

class NoDataException(Exception):
    pass

class LitnetParser():
    _session = None

    def __init__(self, book_id):
        self.book_id = book_id
        self.auth_link = 'https://litnet.com/auth/login?classic=1&link=https://litnet.com/'
        self.book_link = 'https://litnet.com/ru/reader/' + self.book_id
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:67.0) Gecko/20100101 Firefox/67.0'}
        self.user_data = {
                            'LoginForm[login]' : 'pas58@list.ru',
                            'LoginForm[password]': 'OksaVit9788'
                        }
        self.init_book()

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self.headers)
            req = self._session.get(self.auth_link, headers=self.headers)
            soup = BeautifulSoup(req.content, 'html5lib')
            self.user_data['_csrf'] = soup.find('input', attrs={'name': '_csrf'})['value']
            self._session.post(self.auth_link, self.user_data)

        return self._session

    def init_book(self):
        self.ids_array = []
        htmlresp = self.session.get(self.book_link)
        soup = BeautifulSoup(htmlresp.text, 'html5lib')
        all_chapters_ids =soup.find_all('option')
        self.ids_array = [id.get('value') for id in all_chapters_ids]
        self._csrf_tocken = soup.find('input', attrs={'name': '_csrf'})['value']
        self.session.headers.update({
            'origin': 'https://litnet.com',
            'referer': self.book_link,
            'x-csrf-token': self._csrf_tocken
        })

    def _get_page(self, chapter_id, page):

        post_params = {
            'chapterId': chapter_id,
            'page': page,
            '_csrf': self._csrf_tocken
        }

        response_data = self.session.post(
            'https://litnet.com/reader/get-page', post_params
        )
        response_json = json.loads(response_data.text)

        if not response_json['status']:
            raise NoDataException(response_json['data'])

        page_parser = BeautifulSoup(response_json['data'], 'html.parser')

        # Filter from so-called "protection" tags
        for bad_span in page_parser.find_all('span'):
            bad_span.replace_with('')
        [x.extract() for x in page_parser.findAll('i')]

        return page_parser.text, response_json['isLastPage']

    def _get_chapter(self, chapter_id):

        self.session.headers['referer'] = '{}?c={}'.format(
            self.book_link, chapter_id
        )

        total_chapter_text = ''

        try:
            for page in range(1, 10000):
                chapter_text, is_last_page = self._get_page(chapter_id, page)
                total_chapter_text += chapter_text
                if is_last_page:
                    break
                sleep(10)
        except NoDataException as ex:
            print('Error! ', ex)

        total_chapter_text += '\n\n'

        return total_chapter_text

    # def start(self):
    #     print(self._get_chapter(self.ids_array[0]))

    def parse_to_file(self, book_file_name):
        with open(book_file_name, 'wb') as text_file:
            print('Progress: ', end="")
            for index, chapter_id in enumerate(self.ids_array):
                progress = int(index * 100 / len(self.ids_array))
                print(progress, end="..", flush=True)
                text_file.write(self._get_chapter(chapter_id).encode('utf-8'))

            print('100..OK')

def main():
    book_id = input('Введите id книги: ')
    book_file_name = input('Введите название файла(формат .txt): ')
    LitnetParser(book_id).parse_to_file(book_file_name)

if __name__ == '__main__':
    main()