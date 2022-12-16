import requests

def count_words_at_url(url, data):
    resp = requests.post(url, json = data)
    print(resp)
    return resp.text


def say_hello():
    return "hello"