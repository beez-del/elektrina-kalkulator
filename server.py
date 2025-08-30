#!/usr/bin/env python3
"""
Debug verze serveru - ukáže přesný formát dat z API
"""

import json
import requests
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# API endpoints
SPOTOVA_ELEKTRINA_API = "https://spotovaelektrina.cz/api/v1/price/get-prices-json"

@app.route('/')
def serve_app():
    """Servíruje hlavní HTML aplikaci"""
    return send_from_directory('.', 'index.html')

@app.route('/api/debug-api')
def debug_api():
    """Debug endpoint - ukáže co API vrací"""
    try:
        response = requests.get(SPOTOVA_ELEKTRINA_API, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        return jsonify({
            'success': True,
            'raw_response': data,
            'type': str(type(data)),
            'length': len(data) if hasattr(data, '__len__') else 'N/A',
            'first_item': data[0] if isinstance(data, list) and len(data) > 0 else None,
            'first_item_type': str(type(data[0])) if isinstance(data, list) and len(data) > 0 else None,
            'keys': list(data.keys()) if isinstance(data, dict) else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': str(type(e))
        }), 500

@app.route('/api/spot-prices')
@app.route('/api/spot-prices/<date_param>')
def get_spot_prices(date_param='today'):
    """
    Stáhne spotové ceny - s debug výpisy
    """
    try:
        print(f"=== DEBUG: Stahování dat pro: {date_param} ===")
        
        # Určení cílového data
        if date_param == 'tomorrow':
            target_date = (date.today() + timedelta(days=1)).isoformat()
        else:
            target_date = date.today().isoformat()
        
        print(f"Cílové datum: {target_date}")
        
        response = requests.get(SPOTOVA_ELEKTRINA_API, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"=== RAW API RESPONSE ===")
        print(f"Typ dat: {type(data)}")
        print(f"Délka: {len(data) if hasattr(data, '__len__') else 'N/A'}")
        
        if isinstance(data, list):
            print(f"Je to list s {len(data)} položkami")
            if len(data) > 0:
                print(f"První položka: {data[0]}")
                print(f"Typ první položky: {type(data[0])}")
        elif isinstance(data, dict):
            print(f"Je to dict s klíči: {list(data.keys())}")
        else:
            print(f"Neočekávaný typ: {type(data)}")
            
        print(f"Celá odpověď (prvních 500 znaků): {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
        print("=== KONEC RAW RESPONSE ===")
        
        # Zpracování dat
        processed_data = []
        
        # Pokusíme se zpracovat různé možné formáty
        if isinstance(data, list):
            for i, item in enumerate(data):
                print(f"Zpracovávám položku {i}: {item} (typ: {type(item)})")
                
                if isinstance(item, dict):
                    # Standardní formát
                    item_date = item.get('date', '')
                    if item_date == target_date:
                        hour = item.get('hour', 0)
                        price_czk = item.get('price_czk', 0)
                        
                        processed_data.append({
                            'hour': hour,
                            'spotPrice': round(price_czk / 1000, 3),
                            'timestamp': f"{target_date}T{hour:02d}:00:00Z"
                        })
                elif isinstance(item, str):
                    # Možná jsou data jako string JSON?
                    try:
                        parsed_item = json.loads(item)
                        print(f"Parsovaná položka: {parsed_item}")
                        # Pak stejné zpracování...
                    except:
                        print(f"Nelze parsovat string jako JSON: {item}")
                else:
                    print(f"Neznámý typ položky: {type(item)}")
        
        elif isinstance(data, dict):
            # Možná je struktura jiná
            if 'prices' in data:
                prices = data['prices']
                print(f"Našel jsem 'prices' klíč s daty: {type(prices)}")
            elif 'data' in data:
                prices = data['data']
                print(f"Našel jsem 'data' klíč s daty: {type(prices)}")
            else:
                print(f"Dict nemá očekávané klíče, má: {list(data.keys())}")
                prices = data
            
            # Pokračujeme ve zpracování...
        
        print(f"Zpracováno {len(processed_data)} položek")
        
        # Pokud nemáme data, použijeme demo
        if len(processed_data) == 0:
            print("Žádná data nezpracována, generuji demo data")
            processed_data = generate_demo_data()
            source = 'demo_data'
        else:
            source = 'spotovaelektrina.cz'
        
        processed_data.sort(key=lambda x: x['hour'])
        
        return jsonify({
            'success': True,
            'data': processed_data,
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'date': target_date
        })
        
    except Exception as e:
        print(f"CHYBA: {e}")
        print(f"Typ chyby: {type(e)}")
        
        # Vždy vrátíme demo data při chybě
        return jsonify({
            'success': True,
            'data': generate_demo_data(),
            'timestamp': datetime.now().isoformat(),
            'source': 'demo_data',
            'error_fallback': str(e)
        })

def generate_demo_data():
    """Generuje demo data s realistickými cenami"""
    import random
    
    demo_data = []
    for hour in range(24):
        if 1 <= hour <= 5:
            base_price = 1.8 + random.uniform(0, 0.5)
        elif 7 <= hour <= 9:
            base_price = 4.2 + random.uniform(0, 1.0)
        elif 10 <= hour <= 16:
            base_price = 3.2 + random.uniform(0, 0.8)
        elif 17 <= hour <= 20:
            base_price = 4.8 + random.uniform(0, 1.2)
        else:
            base_price = 2.5 + random.uniform(0, 0.8)
        
        demo_data.append({
            'hour': hour,
            'spotPrice': round(base_price, 2),
            'timestamp': f"{date.today().isoformat()}T{hour:02d}:00:00Z"
        })
    
    return demo_data

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
