import scrapy
from urllib.parse import urljoin, urlparse, parse_qs
from scrapy.selector import Selector
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By


class BetwaySpider(scrapy.Spider):
    name = 'betway'
    countries = [
        'eng', 'esp', 'ger', 'ita', 'fra', 'rsa', 'por', 'netherlands', 'usa', 'dza', 'arg', 'aut', 'aut_am', 'aze',
        'bel', 'bol', 'bra', 'bgr', 'canada', 'chi', 'chn', 'col', 'cro', 'cze', 'den', 'denmark_amateur', 'ecu', 'egy',
        'est', 'ethiopia', 'faroe_islands', 'fin', 'geo', 'ger_am', 'gre', 'ice', 'ireland', 'civ', 'jpn', 'kazakhstan',
        'kaz', 'lat', 'lith', 'mas', 'mex', 'mne', 'nzl', 'nir', 'nor', 'par', 'per', 'pol', 'republic_of_korea', 'rou',
        'sco', 'sen', 'singapore', 'spain_amateur', 'swe', 'challenger', 'sui', 'trinidad_and_tobago', 'tun', 'tur_am',
        'ukr', 'ury', 'uzb', 'vnm', 'zambia'
    ]

    def start_requests(self):
        for country in self.countries:
            yield SeleniumRequest(
                url=f'https://www.betway.co.za/sport/soccer/{country}/',
                callback=self.parse,
            )

    def parse(self, response):
        # Use Scrapy selectors to extract the data
        selector = Selector(response)
        # Extract the desired data using CSS or XPath selectors
        relative_game_urls = selector.css(
            'div#fixturesToReplace div.eventRow div#eventDetails_0 > div.inplayStatusDetails.PaddingScreen > a::attr(href)'
        ).getall()
        print('-------------- relative_game_urls ------------')
        print(relative_game_urls)
        filtered_urls = [url for url in relative_game_urls if "datefilter=20240122" in url]
        base_url = 'https://www.betway.co.za/'
        for relative_game_url in filtered_urls:
            absolute_url = urljoin(base_url, relative_game_url)
            parsed_url = urlparse(absolute_url)
            # Extract the path components
            path_components = parsed_url.path.split('/')
            country_code = path_components[3]
            league = path_components[4]
            # Remove underscores
            league_without_underscores = league.replace("_", " ")
            # Capitalize the string
            capitalized_league = league_without_underscores.capitalize()

            # Extract the query parameters
            query_params = parse_qs(parsed_url.query)
            date_time = query_params.get('datefilter', [''])[0]
            event_id = query_params.get('eventId', [''])[0]

            # Extract the date and time from the date_time string
            date = date_time[:8]
            time = date_time[8:]

            original_url = 'https://www.betway.co.za/Bet/EventMultiMarket?' \
                           'eventId=026e4607-0000-0000-0000-000000000000&' \
                           'FeedDataTypeId=00000000-0000-0000-0000-000000000000&' \
                           'isPopular=false&pageNum=1&isFullView=false&loadAll=true'
            new_url = original_url.replace('eventId=026e4607-0000-0000-0000-000000000000', f'eventId={event_id}')

            print('---- New Url-----')
            print(new_url)

            yield scrapy.Request(new_url, callback=self.parse_event, meta={
                'item': {
                    'Country Code': country_code,
                    'League': capitalized_league,
                    'Date': date,
                    'Time': time,
                    'Event ID': event_id
                }
            })

    def parse_event(self, response):
        # Extract the desired data from the response
        country_code = response.meta['item']['Country Code']
        league = response.meta['item']['League']
        date = response.meta['item']['Date']
        time = response.meta['item']['Time']

        home_draw_away_elements = response.css('[data-translate-market="Match Result (1X2)"]').getall()

        home_element = home_draw_away_elements[0]
        away_element = home_draw_away_elements[2]

        home_selector = Selector(text=home_element)
        away_selector = Selector(text=away_element)

        # Extract the text of the data-translate-key attribute
        host_name = home_selector.css('span::attr(data-translate-key)').get()
        guest_name = away_selector.css('span::attr(data-translate-key)').get()

        # Over 1.5
        over15_target_element = response.css('[data-translate-key="Over 1.5"]' '[data-translate-market="Overs/Unders"]')
        over15_parent_xpath = over15_target_element.xpath('parent::node()').xpath('parent::node()')
        over15_element_with_new_line = over15_parent_xpath.css('div.outcome-pricedecimal::text').get()
        try:
            over15 = over15_element_with_new_line.replace('\n', '')
        except AttributeError:
            over15 = None

        # Under 3.5
        under35_target_element = response.css(
            '[data-translate-key="Under 3.5"]' '[data-translate-market="Overs/Unders"]')
        under35_parent_xpath = under35_target_element.xpath('parent::node()').xpath('parent::node()')
        under35_element_with_new_line = under35_parent_xpath.css('div.outcome-pricedecimal::text').get()
        try:
            under35 = under35_element_with_new_line.replace('\n', '')
        except AttributeError:
            under35 = None

        # BTTS Yes
        btts_yes_target_element = response.css(
            '[data-translate-key="Yes"]' '[data-translate-market="Both Teams To Score"]')
        btts_yes_parent_xpath = btts_yes_target_element.xpath('parent::node()').xpath('parent::node()')
        btts_yes_element_with_new_line = btts_yes_parent_xpath.css('div.outcome-pricedecimal::text').get()
        try:
            btts_yes = btts_yes_element_with_new_line.replace('\n', '')
        except AttributeError:
            btts_yes = None

        # BTTS No
        btts_no_target_element = response.css(
            '[data-translate-key="No"]' '[data-translate-market="Both Teams To Score"]')
        btts_no_parent_xpath = btts_no_target_element.xpath('parent::node()').xpath('parent::node()')
        btts_no_element_with_new_line = btts_no_parent_xpath.css('div.outcome-pricedecimal::text').get()
        try:
            btts_no = btts_no_element_with_new_line.replace('\n', '')
        except AttributeError:
            btts_no = None

        # Draw no bet
        draw_no_bet_odds_target_elements = response.css('[data-translate-market="Draw No Bet"]')

        # Home Draw no bet odds
        if len(draw_no_bet_odds_target_elements) >= 1:
            home_draw_no_bet_odds_target_element = draw_no_bet_odds_target_elements[0]
            home_draw_no_bet_odds_parent_xpath = home_draw_no_bet_odds_target_element.xpath('parent::node()').xpath(
                'parent::node()')
            home_draw_no_bet_odds_element_with_new_line = home_draw_no_bet_odds_parent_xpath.css(
                'div.outcome-pricedecimal::text').get()
            home_draw_no_bet_odds = home_draw_no_bet_odds_element_with_new_line.replace('\n', '')
        else:
            home_draw_no_bet_odds = None

        # Away Draw no bet odds
        if len(draw_no_bet_odds_target_elements) >= 2:
            away_draw_no_bet_odds_target_element = draw_no_bet_odds_target_elements[1]
            away_draw_no_bet_odds_parent_xpath = away_draw_no_bet_odds_target_element.xpath('parent::node()').xpath(
                'parent::node()')
            away_draw_no_bet_odds_element_with_new_line = away_draw_no_bet_odds_parent_xpath.css(
                'div.outcome-pricedecimal::text').get()
            away_draw_no_bet_odds = away_draw_no_bet_odds_element_with_new_line.replace('\n', '')
        else:
            away_draw_no_bet_odds = None


        yield {
            'Country Code': country_code,
            'League': league,
            'Date': date,
            'Time': time,
            'host_name': host_name,
            'guest_name': guest_name,
            'Over 1.5': over15,
            'Under 3.5': under35,
            'BTTS Yes': btts_yes,
            'BTTS No': btts_no,
            'Home Draw No Bet Odds': home_draw_no_bet_odds,
            'Away Draw No Bet Odds': away_draw_no_bet_odds,

        }

    def selenium(self, response):
        self.selenium.get(response.url)
        self.selenium.wait_until_page_contains_element((By.CSS_SELECTOR, 'div#fixturesToReplace'))
        return self.selenium

    """
     # Home odds
     home_odds_target_element = response.xpath(
         '//span[@data-translate-market="Match Result (1X2)" and @data-translate-key=$team]', team=HOST_NAME)
     home_odds_parent_xpath = home_odds_target_element.xpath('parent::node()').xpath('parent::node()')
     home_odds_element_with_new_line = home_odds_parent_xpath.css('div.outcome-pricedecimal::text').get()
     home_odds = home_odds_element_with_new_line.replace('\n', '')

     # Draw
     draw_target_element = response.css('[data-translate-key="Draw"]' '[data-translate-market="Match Result (1X2)"]')
     draw_parent_xpath = draw_target_element.xpath('parent::node()').xpath('parent::node()')
     draw_element_with_new_line = draw_parent_xpath.css('div.outcome-pricedecimal::text').get()
     draw = draw_element_with_new_line.replace('\n', '')

     # Away odds
     away_odds_target_element = response.xpath(
         '//span[@data-translate-market="Match Result (1X2)" and @data-translate-key=$team]', team=GUEST_NAME)
     away_odds_parent_xpath = away_odds_target_element.xpath('parent::node()').xpath('parent::node()')
     away_odds_element_with_new_line = away_odds_parent_xpath.css('div.outcome-pricedecimal::text').get()
     away_odds = away_odds_element_with_new_line.replace('\n', '')



     # Home Total Over 0.5 odds
     home_total_over05_odds_target_element = response.xpath(
         '//span[@data-translate-market=$team and @data-translate-key="Over 0.5"]', team=HOST_NAME + ' Total')
     home_total_over05_odds_parent_xpath = home_total_over05_odds_target_element.xpath('parent::node()').xpath(
         'parent::node()')
     home_total_over05_odds_element_with_new_line = home_total_over05_odds_parent_xpath.css(
         'div.outcome-pricedecimal::text').get()
     home_total_over05_odds = home_total_over05_odds_element_with_new_line.replace('\n', '')

     # Home Total Under 2.5 odds
     home_total_under25_odds_target_element = response.xpath(
         '//span[@data-translate-market=$team and @data-translate-key="Under 2.5"]', team=HOST_NAME + ' Total')
     home_total_under25_odds_parent_xpath = home_total_under25_odds_target_element.xpath('parent::node()').xpath(
         'parent::node()')
     home_total_under25_odds_element_with_new_line = home_total_under25_odds_parent_xpath.css(
         'div.outcome-pricedecimal::text').get()
     home_total_under25_odds = home_total_under25_odds_element_with_new_line.replace('\n', '')

     # Away Total Over 0.5 odds
     away_total_over05_odds_target_element = response.xpath(
         '//span[@data-translate-market=$team and @data-translate-key="Over 0.5"]', team=GUEST_NAME + ' Total')
     away_total_over05_odds_parent_xpath = away_total_over05_odds_target_element.xpath('parent::node()').xpath(
         'parent::node()')
     away_total_over05_odds_element_with_new_line = away_total_over05_odds_parent_xpath.css(
         'div.outcome-pricedecimal::text').get()
     away_total_over05_odds = away_total_over05_odds_element_with_new_line.replace('\n', '')

     # Away Total Under 2.5 odds
     away_total_under25_odds_target_element = response.xpath(
         '//span[@data-translate-market=$team and @data-translate-key="Under 2.5"]', team=GUEST_NAME + ' Total')
     away_total_under25_odds_parent_xpath = away_total_under25_odds_target_element.xpath('parent::node()').xpath(
         'parent::node()')
     away_total_under25_odds_element_with_new_line = away_total_under25_odds_parent_xpath.css(
         'div.outcome-pricedecimal::text').get()
     away_total_under25_odds = away_total_under25_odds_element_with_new_line.replace('\n', '')
     
     
     import pandas as pd
import re

# Assuming you have two dataframes: df1 and df2

# Merge based on 'host_name' and 'home_team' using string contains
merged_df1 = pd.merge(df1, df2, left_on=df1['host_name'].apply(lambda x: any(re.search(team, x) for team in df2['home_team'])),
                      right_on='home_team')

# Merge based on 'guest_name' and 'away_team' using string contains
merged_df2 = pd.merge(df1, df2, left_on=df1['guest_name'].apply(lambda x: any(re.search(team, x) for team in df2['away_team'])),
                      right_on='away_team')


     """
