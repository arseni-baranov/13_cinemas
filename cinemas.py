from bs4 import BeautifulSoup
import requests
import re
import random
import argparse


afisha_url = "http://www.afisha.ru/msk/schedule_cinema/"
kinopoisk_url = "http://kinopoisk.ru/index.php"

proxy_list = "http://www.freeproxy-list.ru/api/proxy?anonymity=false&token=demo"
proxy_re = re.compile(r'\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:\d{1,4}')

user_agents = [
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
    html = requests.get(proxy_list).text
    proxies = html.split('\n')
    return proxies


def parse_afisha_page(max=10):
    soup = BeautifulSoup(requests.get(afisha_url).text, "html.parser")

    schedule = soup.find_all("div", id="schedule")[0]
    divs = schedule.find_all("h3", class_="usetags", limit=max)
    theater_tbl = schedule.find_all("table", limit=max)

    return [movie.find("a").text for movie in divs], \
           [len(theaters.findAll("td", class_="b-td-item")) for theaters in theater_tbl]


def fetch_movies(movies, proxies):
    session = requests.Session()

    for title in movies:
        while 1:
            try:
                print("Fetching movie:", title)
                payload = {"kp_query": title, "first": "yes"}
                header = {'User-Agent': random.choice(user_agents)}
                proxy = {"http": random.choice(proxies)}
                movie_html = session.get(kinopoisk_url, params=payload, timeout=10, headers=header, proxies=proxy).text

                soup = BeautifulSoup(movie_html, "html.parser")
                movie_in_production = soup.findAll('td', text=re.compile('статус производства:'))
                if movie_in_production:
                    rating, people_rated = '?', '?'
                else:
                    rating = soup.find("span", class_="rating_ball").text
                    people_rated = soup.find("span", class_="ratingCount").text.replace(u'\xa0', u' ')
            except (AttributeError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError,
                    requests.exceptions.ProxyError, requests.exceptions.ReadTimeout) as error:
                print('\nError:', error)
                print('trying again...\n')
            else:
                break

        yield [rating, people_rated]


def print_movies(movie_data, cinema_sort=False):
    if cinema_sort:
        sorting_function = lambda el: el[1]
    else:
        sorting_function = lambda el: el[2][0]

    movie_data.sort(key=sorting_function, reverse=True)

    for item in movie_data:
        print("\n{0}:\nПоказ в {1} кинотеатрах\nНабрал: {2} по оценкам {3} пользователей"
              .format(item[0], item[1], item[2][0], item[2][1]), sep="\n")


def main():
    args = get_console_args()
    number_of_movies = int(args.quantity)
    movies, theaters = parse_afisha_page(number_of_movies)
    proxies = get_proxies_list()
    scores = []

    for item in fetch_movies(movies, proxies):
        scores.append(item)

    movie_data = list(zip(movies, theaters, scores))
    sorting = bool(args.showings)
    print_movies(movie_data, cinema_sort=sorting)

if __name__ == "__main__":
    main()
