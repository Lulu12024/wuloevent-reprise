import requests
from django.core.management.base import BaseCommand

# RUN echo "indices.query.bool.max_clause_count: 1000000" >> /usr/share/elasticsearch/config/elasticsearch.yml
# curl -XPUT -H "Content-Type: application/json" http://localhost:9200/_cluster/settings -d '{ "transient": { "cluster.routing.allocation.disk.threshold_enabled": false } }'
# curl -XPUT -H "Content-Type: application/json" http://localhost:9200/_all/_settings -d '{"index.blocks.read_only_allow_delete": null}'


data1 = '{ "transient": { "cluster.routing.allocation.disk.threshold_enabled": false } }'

data2 = '{"index.blocks.read_only_allow_delete": null}'

url1 = 'http://wuloevents.elasticsearch:9200/_cluster/settings'
url2 = 'http://wuloevents.elasticsearch:9200/_all/_settings'

headers = {'content-type': 'application/json'}


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def handle(self, *args, **options):
        loop = True
        while loop:
            try:
                request1 = requests.put(url1, data=data1, headers=headers)
                request2 = requests.put(url2, data=data2, headers=headers)
                if int(request1.status_code) == 200 and int(request1.status_code) == 200:
                    loop = False
            except Exception as exc:
                print(exc)
