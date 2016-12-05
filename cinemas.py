""" Получает топ 10 самых рейтинговых фильмов которые на сегодянший день идут в кино
    Использует прокси для обхода бана со стороны кинопоиска
    
    Стандартная сортировка идёт по общему рейнигу, возможна сортировка по количествам кинотеатров
    в которых идёт показ
"""

from bs4 import BeautifulSoup
import requests
import re
import random
import argparse


class Constants:
    afisha_url = "http://www.afisha.ru/msk/schedule_cinema/"
    kinopoisk_url = "http://kinopoisk.ru/index.php"

    proxy_list = "http://www.freeproxy-list.ru/api/proxy?anonymity=false&token=demo"
    proxy_re = re.compile(r'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:\d{1,4}')

    proxies = []

    user_agents = [
        'Mozilla/5.0 (X11; Linux i686; rv:50.0) Gecko/20100101 Firefox/50.0',
        'Opera/9.80 (Windows NT 6.2; WOW64) Presto/2.12.388 Version/12.17',
        'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0'
    ]


def get_console_args():
    parser = argparse.ArgumentParser(description="Shows top 10 movies sorted by rating currently in cinemas")
    parser.add_argument("--showings", "--s", help="Sort movies by cinema showings", action='store_true')
    args = parser.parse_args()

    return args


def get_proxies_list():
    html = requests.get(Constants.proxy_list).text
    Constants.proxies = html.split('\n')


def parse_afisha_page(max=10):
    soup = BeautifulSoup(requests.get(Constants.afisha_url).text, "html.parser")

    schedule = soup.find_all("div", id="schedule")[0]
    divs = schedule.find_all("h3", class_="usetags", limit=max)
    theater_tbl = schedule.find_all("table", limit=max)

    return [movie.find("a").text for movie in divs], \
           [len(theaters.findAll("td", class_="b-td-item")) for theaters in theater_tbl]


def proxy_fetch_movies(movies, proxies_func=lambda: get_proxies_list(), debug_mode=True):

    """ Получает список случайных прокси (для избежания бана со стороны кинопоиска),
        парсит рейтинг и количество проголосовавших пользователей используя при этом
        случайный прокси из полученного списка

    :param movies: список названий фильмов
    :param proxies_func: функция которая собирает случайные прокси
                                    (в виде: 123.123.123.123:0000 \n)
                                    
    :param debug_mode: Вывод сообщений об ошибках

    :return: Список с общими рейтингами и количеством проголосовавших пользователей
    """

    ratings = []
    session = requests.Session()

    proxies_func()

    for title in movies:
        await = 20
        while 1:
            try:
                print("Fetching movie:", title)
                payload = {"kp_query": title, "first": "yes"}
                header = {'User-Agent': random.choice(Constants.user_agents)}
                proxies = {"http": random.choice(Constants.proxies)}

                movie_html = session.get(Constants.kinopoisk_url, params=payload, headers=header,
                                         timeout=await, proxies=proxies).text

                soup = BeautifulSoup(movie_html, "html.parser")
                rating = soup.find("span", class_="rating_ball").text
                people_rated = soup.find("span", class_="ratingCount").text.replace(u'\xa0', u' ')
            except BaseException as error:
                if debug_mode:
                    print('\nError:', error)
                    print('trying again...\n')
                await += 10
            else:
                ratings.append([rating, people_rated])
                break
    return ratings


def output_movies(movie_data, cinema_sort=False):

    # Отсортируем фильмы по рейтингу

    if cinema_sort:
        movie_data.sort(key=lambda el: el[1], reverse=True)
    else:
        movie_data.sort(key=lambda el: el[2][0], reverse=True)

    for item in movie_data:
        print("{0}:\nПоказ в {1} кинотеатрах\nНабрал: {2} по оценкам {3} пользователей\n"
              .format(item[0], item[1], item[2][0], item[2][1]), sep="\n")


def main():
    args = get_console_args()
    movies, theaters = parse_afisha_page()
    scores = proxy_fetch_movies(movies)
    movie_data = list(zip(movies, theaters, scores))

    if args.showings:
        output_movies(movie_data, cinema_sort=True)
    else:
        output_movies(movie_data, cinema_sort=False)


if __name__ == "__main__":
    main()
