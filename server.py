#!/usr/bin/env python3
"""
Proxy server pro stahování spotových cen elektřiny z OTE
Řeší CORS problémy pro webovou aplikaci
"""

import json
import requests
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys

app = Flask(__name__)
CORS(app)  # Povolí CORS pro všechny domény

# API endpoints
SPOTOVA_ELEKTRINA_API = "https://spotovaelektrina.cz/api/v1/price/get-prices-json"

@app.route('/')
def serve_app():
    """Servíruje hlavní HTML aplikaci"""
    return send_from_directory('.', 'index.html')

@app.route('/api/spot-prices')
@app.route('/api/spot-prices/<date_param>')
def get_spot_prices(date_param='today'):
    """
    Stáhne spotové ceny z spotovaelektrina.cz
    Parametry:
    - today: dnešní ceny
    - tomorrow: zítřejší ceny
    """
    try:
        print(f"Stahování dat pro: {date_param}")
        response = requests.get(SPOTOVA_ELEKTRINA_API, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"API odpověď: {type(data)}, klíče: {list(data.keys()) if isinstance(data, dict) else 'není dict'}")
        
        # Určení cílového data
        if date_param == 'tomorrow':
            target_date = (date.today() + timedelta(days=1)).isoformat()
        else:
            target_date = date.today().isoformat()
        
        # Zpracování dat podle skutečného formátu API
        processed_data = []
        
        if isinstance(data, dict):
            # Vybereme správnou datovou sadu podle parametru
            if date_param == 'tomorrow' and 'hoursTomorrow' in data:
                hours_data = data['hoursTomorrow']
                print(f"Používám hoursTomorrow: {len(hours_data)} hodin")
            elif 'hoursToday' in data:
                hours_data = data['hoursToday'] 
                print(f"Používám hoursToday: {len(hours_data)} hodin")
            else:
                print("Neznámý formát dat z API")
                hours_data = []
            
            # Zpracování hodinových dat
            for item in hours_data:
                hour = item.get('hour', 0)
                price_czk = item.get('priceCZK', 0)  # Pozor: priceCZK, ne price_czk!
                
                processed_data.append({
                    'hour': hour,
                    'spotPrice': round(price_czk / 1000, 2),  # převod z Kč/MWh na Kč/kWh
                    'timestamp': f"{target_date}T{hour:02d}:00:00Z"
                })
        
        # Pokud nemáme data pro požadované datum
        if len(processed_data) == 0:
            print(f"Žádná data pro {date_param}")
            return jsonify({
                'success': True,
                'data': [],
                'message': f'Data pro {date_param} nejsou k dispozici',
                'timestamp': datetime.now().isoformat(),
                'source': 'spotovaelektrina.cz',
                'date': target_date
            })
        
        # Seřadíme podle hodin
        processed_data.sort(key=lambda x: x['hour'])
        
        return jsonify({
            'success': True,
            'data': processed_data,
            'timestamp': datetime.now().isoformat(),
            'source': 'spotovaelektrina.cz',
            'date': target_date
        })
        
    except requests.RequestException as e:
        print(f"Chyba při stahování dat: {e}")
        
        return jsonify({
            'success': False,
            'data': [],
            'message': 'Služba není dostupná',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503
    
    except Exception as e:
        print(f"Neočekávaná chyba: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/debug-api')
def debug_api():
    """Debug endpoint pro kontrolu API odpovědi"""
    try:
        response = requests.get(SPOTOVA_ELEKTRINA_API, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Základní info o odpovědi
        debug_info = {
            'success': True,
            'type': str(type(data)),
            'length': len(data) if hasattr(data, '__len__') else 'N/A'
        }
        
        if isinstance(data, dict):
            debug_info['keys'] = list(data.keys())
            if 'hoursToday' in data:
                debug_info['hoursToday_length'] = len(data['hoursToday'])
                debug_info['first_today'] = data['hoursToday'][0] if data['hoursToday'] else None
            if 'hoursTomorrow' in data:
                debug_info['hoursTomorrow_length'] = len(data['hoursTomorrow'])
                debug_info['first_tomorrow'] = data['hoursTomorrow'][0] if data['hoursTomorrow'] else None
        elif isinstance(data, list):
            debug_info['first_item'] = data[0] if data else None
            debug_info['first_item_type'] = str(type(data[0])) if data else None
        
        debug_info['raw_response'] = data
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

def generate_demo_data():
    """Generuje demo data s realistickými cenami"""
    import random
    
    demo_data = []
    for hour in range(24):
        # Realistické ceny podle denního profilu
        if 1 <= hour <= 5:  # Noční minimum
            base_price = 1.8 + random.uniform(0, 0.5)
        elif 7 <= hour <= 9:  # Ranní špička
            base_price = 4.2 + random.uniform(0, 1.0)
        elif 10 <= hour <= 16:  # Den
            base_price = 3.2 + random.uniform(0, 0.8)
        elif 17 <= hour <= 20:  # Večerní špička
            base_price = 4.8 + random.uniform(0, 1.2)
        else:  # Ostatní časy
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
    # Pro lokální vývoj
    port = int(os.environ.get('PORT', 3000))
    
    print("=" * 50)
    print("🚀 PROXY SERVER PRO SPOTOVÉ CENY ELEKTŘINY")
    print("=" * 50)
    print(f"📍 Server běží na portu: {port}")
    print("=" * 50)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
else:
    # Pro produkční nasazení (gunicorn)
    # Žádná dodatečná konfigurace není potřeba
    pass
