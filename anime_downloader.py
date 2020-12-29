'''
@author: Antonio Fusco
https://github.com/fuscoantonio
'''

import sys
sys.path.insert(1, './utilities')
from requests import Session
from requests.exceptions import HTTPError, ConnectionError
from bs4 import BeautifulSoup
from pathlib import Path
import vvvvid_downloader
from utils import download, ask_episodes_numbers, list_options

SITE_URL = 'https://www.animeworld.tv'
GOOGLE_SEARCH_URL = 'https://www.google.com/search?q='
DOWNLOAD_PATH = Path.cwd() / Path('Downloads')


def main():
    print("### Anime Downloader NON ufficiale, visita animeworld.tv e vvvvid.it ###\n")
    with Session() as session:
        while True:
            try:
                results_html = get_search_results(session)
                anime_title = ask_selecting_title(session, results_html)
                anime_html = get_anime_html(session, results_html, anime_title)
                if anime_html:
                    start_download_process(session, anime_html, anime_title)
                else:
                    use_vvvvid_downloader(anime_title)
            except HTTPError:
                print("### Si e' verificato un errore durante la richiesta al server. Riprova.###")
                exit()
            except ConnectionError:
                print('### Errore di connessione, verifica la tua connessione ad internet. ###')
                exit()
            except Exception as e:
                print(e)



def start_download_process(session: Session, anime_html: BeautifulSoup, anime_title: str):
    episodes = anime_html.select('.server.active .episodes.range .episode a')
    first_episode_num = int(episodes[0].getText())
    last_episode_num = int(episodes[-1].getText())
    episodes_numbers = ask_episodes_numbers(anime_title, len(episodes), first_episode_num, last_episode_num)
    download_episodes(session, episodes, episodes_numbers, anime_title)



def download_episodes(session: Session, episodes: BeautifulSoup, episodes_numbers, anime_title: str):
    is_one_episode = len(episodes) == 1
    is_any_downloaded = False

    for episode in episodes:
        episode_num = episode.getText()
        if int(episode_num) in episodes_numbers:
            try:
                url = request_filtered_html(session, SITE_URL, episode.get('href'), '#alternativeDownloadLink')
                url = url[0].get('href')
                download_anime_path = download(anime_title, episode_num, url, DOWNLOAD_PATH, is_one_episode)

                if download_anime_path is not None:
                    is_any_downloaded = True
            except:
                print(f"Non e' stato possibile scaricare l'episodio {episode_num}")
    
    if is_any_downloaded:
        print(f"I download si trovano in {download_anime_path}\n")



def use_vvvvid_downloader(anime_title: str):
    anime_id = get_vvvvid_anime_id(anime_title)
    if anime_id:
        vvvvid_downloader.run(anime_id)
    else:
        print(f"Non e' possibile scaricare {anime_title}.")



def get_vvvvid_anime_id(anime_title: str) -> str:
    """ Extracts the show id from the url of the first google result and returns it. """
    search_query = 'vvvvid+' + anime_title.replace(' ', '+')
    google_results = request_filtered_html(Session(), GOOGLE_SEARCH_URL, search_query, 'div div a')

    vvvvid_url = None
    for result in google_results:
        if '/url?q=https://www.vvvvid.it/' in result.get('href'):
            vvvvid_url = result.get('href')
            break
    
    anime_id = None
    if vvvvid_url:
        #extracts id from vvvvid url
        anime_id = vvvvid_url.replace('/url?q=https://www.vvvvid.it/show/', '')
        anime_id = anime_id.rsplit('/', 1)[0]

    return anime_id



def get_search_results(session: Session) -> list: 
    results = None
    while not results:
        title_to_search = ask_search_title()
        results = search_title(session, title_to_search)
        if not results:
            print(f'Nessun risultato per {title_to_search}.')
    
    return results



def ask_search_title() -> str:
    search_title = None
    while not search_title:
        try:
            search_title = input("Cerca un anime: ")
            if not search_title:
                print("Il nome non puo' essere vuoto.")
        except KeyboardInterrupt:
            exit()
    
    return search_title



def search_title(session: Session, title_to_search: str) -> list:
    title_to_search = title_to_search.replace(' ', '+')
    url_part = '/search?keyword='+title_to_search
    results_html = request_filtered_html(session, SITE_URL, url_part, '.film-list .name')
    
    return results_html



def ask_selecting_title(session: Session, results_html: list) -> str:
    results_titles = [item.getText() for item in results_html]
    chosen_title = list_options('Seleziona uno di questi risultati', results_titles)

    return chosen_title



def get_anime_html(session: Session, results_html: list, selected_title: str) -> BeautifulSoup:
    """ Returns chosen anime's whole page's html if direct download or vvvvid are available,
        otherwise returns None. """
    for result in results_html:
        if result.getText() == selected_title:
            anime_url = result.get('href')
    
    anime_page_html = request_html(session, SITE_URL, anime_url)

    if not is_direct_download_available(anime_page_html):
        if is_vvvvid_available(anime_page_html):
            anime_page_html = None
        else:
            raise Exception(f"Non e' possibile scaricare {selected_title}.")

    return anime_page_html



def is_direct_download_available(page_html: BeautifulSoup) -> bool:
    is_available = True
    download_section = page_html.select('#download')

    if download_section:
        #trying to retrieve the alternative download link of the first episode
        alternative_link = page_html.select('#alternativeDownloadLink')[0].get('href')
        if not alternative_link:
            is_available = False
    else:
        is_available = False

    return is_available



def is_vvvvid_available(page_html: BeautifulSoup) -> bool:
    servers = page_html.select('.server-tab')
    is_available = any(server.getText() == 'VVVVID' for server in servers)

    return is_available



def request_html(session: Session, base_url: str, url_part: str) -> BeautifulSoup: 
    response = session.get(f'{base_url}{url_part}')
    response.raise_for_status()
    html_data = BeautifulSoup(response.text, 'html.parser')
    
    return html_data



def request_filtered_html(session: Session, base_url: str, url_part: str, selector: str) -> list:
    response = session.get(f'{base_url}{url_part}')
    response.raise_for_status()
    html_data = BeautifulSoup(response.text, 'html.parser')
    html_data = html_data.select(selector)

    return html_data



if __name__ == '__main__':
    main()