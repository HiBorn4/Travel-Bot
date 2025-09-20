
import pandas as pd

city_excel_path = 'citynames.xlsx'
purpose_excel_path = 'Travel-Purpose.xlsx'

def get_valid_cities(city_excel_path):
    df = pd.read_excel(city_excel_path)
    city_map = dict(zip(df['City'], df['City_Code']))
    return city_map

def get_valid_purposes(purpose_excel_path):
    df = pd.read_excel(purpose_excel_path)
    return df['Travel Purpose'].dropna().unique().tolist()
