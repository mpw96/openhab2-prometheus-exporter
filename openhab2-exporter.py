#!/usr/bin/python3

import argparse
import http.server
import socketserver
import sys
import time

import requests

openhab_hostname = None
openhab_port = None

def get_metrics():

    payload = {
        'recursive': 'false',
        'fields': 'name,state,type',
    }
    with requests.Session() as metrics_session:
        resp = metrics_session.get(url=f'http://{openhab_hostname}:{openhab_port}/rest/items', params=payload)

    obj = resp.json()
    ts = int(round(time.time() * 1000))

    numbers = [ item for item in obj if item['type'].lower() == 'number' ]
    dimmers = [ item for item in obj if item['type'].lower() == 'dimmer' ]
    switches = [ item for item in obj if item['type'].lower() == 'switch' ]
    contacts = [ item for item in obj if item['type'].lower() == 'contact' ]

    res = ''
    res = res + print_metrics(numbers, 'number', ts)
    res = res + print_metrics(dimmers, 'dimmer', ts)
    res = res + print_metrics(switches, 'switch', ts)
    res = res + print_metrics(contacts, 'contact', ts)

    return res.encode('utf-8')


def print_metrics(metrics, itype, timestamp):
    metric_name = f'openhab2_metric_{itype}'

    res = f'# TYPE {metric_name} gauge\n'

    for metric in metrics:
        name = metric['name']
        value = metric['state']

        if value is None or value == 'NULL':
            continue

        if metric['type'].lower() == 'switch':
            value = 1 if value == 'ON' else 0
        elif metric['type'].lower() == 'contact':
            value = 1 if value == 'OPEN' else 0

        res = res + metric_name + '{name="' + name + '"} ' + '{} {}\n'.format(value, timestamp)

    return res

class OpenHABMetricsHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        content = get_metrics()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OpenHAB2 Metrics Exporter (Prometheus).')
    parser.add_argument('listen_port', help='Endpoint of this metrics exporter')
    parser.add_argument('--openhab_hostname', default='localhost', help='Hostname of the openhab server')
    parser.add_argument('--openhab_port', default='8080', help='Port where OpenHAB2 listens')

    args = parser.parse_args()

    openhab_hostname = args.openhab_hostname
    openhab_port = args.openhab_port

    with socketserver.TCPServer(("", int(args.listen_port)), OpenHABMetricsHandler) as httpd:
        print("serving at port", args.listen_port)
        httpd.serve_forever()
