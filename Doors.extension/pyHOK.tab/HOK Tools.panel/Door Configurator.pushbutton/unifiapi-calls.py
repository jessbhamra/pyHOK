import requests

# Replace with your Unifi API key
API_KEY = 'your_api_key_here'
# Base URL for the Unifi API
BASE_URL = 'https://api.unifilabs.com/v2'

# Headers for the requests
headers = {
    'Authorization': 'Bearer ' + API_KEY,
    'Content-Type': 'application/json'
}

def get_family_content(family_id):
    """
    Function to get Revit family content by family ID
    """
    url = BASE_URL + '/content/download'
    params = {
        'family_id': family_id
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        content = response.content
        filename = family_id + '.rfa'
        with open(filename, 'wb') as file:
            file.write(content)
        print('Downloaded:', filename)
    else:
        print('Failed to download content:', response.status_code, response.text)

# Example usage
family_id = 'your_family_id_here'
get_family_content(family_id)
