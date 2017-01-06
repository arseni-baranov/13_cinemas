from bs4 import BeautifulSoup
import requests
import re
import random
import argparse
import logging


AFISHA_URL = "http://www.afisha.ru/msk/schedule_cinema/"
KINOPOISK_URL = "http://kinopoisk.ru/index.php"

PROXY_LIST = "http://www.freeproxy-list.ru/api/proxy?anonymity=false&token=demo"
PROXY_RE = re.compile(r'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:\d{1,4}')

USER_AGENTS = [
    'Mozilla/5.0 (X11; Linux i686; rv:50.0) Gecko/20100101 Firefox/50.0',
    'Opera/9.80 (Windows NT 6.2; WOW64) Presto/2.12.388 Version/12.17',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0'
]


def get_console_args():
    parser = argparse.ArgumentParser(description="Shows top 10 movies sorted by rating currently in cinemas")
    parser.add_argument("--showings", "--s", help="Sort movies by cinema showings", action='store_true')
    parser.add_argument("--quantity", "--q", help="Number of movies to print", default=10)
    args = parser.parse_args()

    return args


def get_proxies_list():
    html = requests.get(PROXY_LIST).text
    proxies = html.split('\n')
    return proxies


def parse_afisha_page(amount=10):
    soup = BeautifulSoup(requests.get(AFISHA_URL).text, "html.parser")

    schedule = soup.find_all("div", id="schedule")[0]
    divs = schedule.find_all("h3", class_="usetags", limit=amount)
    theater_tbl = schedule.find_all("table", limit=amount)

    return [movie.find("a").text for movie in divs], \
           [len(theaters.findAll("td", class_="b-td-item")) for theaters in theater_tbl]


def fetch_movie(title, proxy):
    session = requests.Session()
    payload = {"kp_query": title, "first": "yes"}
    header = {'User-Agent': random.choice(USER_AGENTS)}
    movie_html = session.get(KINOPOISK_URL, params=payload, timeout=10, headers=header, proxies=proxy).text
    soup = BeautifulSoup(movie_html, "html.parser")

    try:
        rating = soup.find("span", class_="rating_ball").text
        people_rated = soup.find("span", class_="ratingCount").text.replace(u'\xa0', u' ')
    except AttributeError:
        rating, people_rated = None, None

    return rating, people_rated


def collect_movies_log_status(movies, proxies, max_tries=10):
    for title in movies:
        try_counter = 0
        while try_counter < max_tries:
            logging.debug("Fetching movie: {}".format(title))
            proxy = {"http": random.choice(proxies)}
            try:
                rating, people_rated = fetch_movie(title, proxy)
            except IOError:
                logging.error('Error with parsing movie, trying again...\n')
                try_counter += 1
            else:
                yield rating, people_rated
                break


def sort_movies(movie_data, cinema_sort=False):
    if cinema_sort:
        sorting_function = lambda el: el[1]
    else:
        sorting_function = lambda el: el[2][0]

    movie_data.sort(key=sorting_function, reverse=True)

    return movie_data


def print_movies(movie_data):
    for item in movie_data:
        print("\n{0}:\nПоказ в {1} кинотеатрах\nНабрал: {2} по оценкам {3} пользователей"
              .format(item[0], item[1], item[2][0], item[2][1]), sep="\n")


def main():
    args = get_console_args()
    number_of_movies = int(args.quantity)
    movies, theaters = parse_afisha_page(number_of_movies)
    proxies = get_proxies_list()
    scores = []

    logging.basicConfig(filename="logfile.log", level=logging.DEBUG)

    for item in collect_movies_log_status(movies, proxies):
        if item is None:
            scores.append('')

    movie_data = list(zip(movies, theaters, scores))
    sorting = bool(args.showings)
    sorted_data = sort_movies(movie_data, cinema_sort=sorting)
    print_movies(sorted_data)


if __name__ == "__main__":
    main()
