# From https://github.com/dshvadskiy/search_with_machine_learning_course/blob/main/index_products.py
import requests
from lxml import etree

import click
import glob
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(levelname)s:%(message)s')

# NOTE: this is not a complete list of fields.  If you wish to add more, put in the appropriate XPath expression.
# TODO: is there a way to do this using XPath/XSL Functions so that we don't have to maintain a big list?
mappings = [
    "sku/text()", "sku", # SKU is the unique ID, productIds can have multiple skus
    "productId/text()", "productId",
    "name/text()", "name",
    "type/text()", "type",
    "regularPrice/text()", "regularPrice",
    "salePrice/text()", "salePrice",
    "onSale/text()", "onSale",
    "salesRankShortTerm/text()", "salesRankShortTerm",
    "salesRankMediumTerm/text()", "salesRankMediumTerm",
    "salesRankLongTerm/text()", "salesRankLongTerm",
    "bestSellingRank/text()", "bestSellingRank",
    "url/text()", "url",
    "categoryPath/*/name/text()", "categoryPath",  # Note the match all here to get the subfields
    "categoryPath/*/id/text()", "categoryPathIds",  # Note the match all here to get the subfields
    "categoryPath/category[last()]/id/text()", "categoryLeaf",
    "count(categoryPath/*/name)", "categoryPathCount",
    "customerReviewCount/text()", "customerReviewCount",
    "customerReviewAverage/text()", "customerReviewAverage",
    "inStoreAvailability/text()", "inStoreAvailability",
    "onlineAvailability/text()", "onlineAvailability",
    "releaseDate/text()", "releaseDate",
    "shortDescription/text()", "shortDescription",
    "class/text()", "class",
    "classId/text()", "classId",
    "department/text()", "department",
    "departmentId/text()", "departmentId",
    "bestBuyItemId/text()", "bestBuyItemId",
    "description/text()", "description",
    "manufacturer/text()", "manufacturer",
    "modelNumber/text()", "modelNumber",
    "image/text()", "image",
    "longDescription/text()", "longDescription",
    "longDescriptionHtml/text()", "longDescriptionHtml",
    "features/*/text()", "features"  # Note the match all here to get the subfields

]


def get_opensearch():
    host = 'localhost'
    port = 9200
    auth = ('admin', 'admin')

    #### Step 2.a: Create a connection to OpenSearch
    client = OpenSearch(
        hosts = [{'host': host, 'port': port}],
        http_compress = True, # enables gzip compression for request bodies
        http_auth = auth,
        # client_cert = client_cert_path,
        # client_key = client_key_path,
        use_ssl = True,
        verify_certs = False,
        ssl_assert_hostname = False,
        ssl_show_warn = False,
    )
    return client


@click.command()
@click.option('--source_dir', '-s', help='XML files source directory')
@click.option('--index_name', '-i', default="bbuy_products", help="The name of the index to write to")
def main(source_dir: str, index_name: str):
    client = get_opensearch()
    # To test on a smaller set of documents, change this glob to be more restrictive than *.xml
    files = glob.glob(source_dir + "/*.xml")
    # files = ["/workspace/datasets/product_data/products/products_0001_2570_to_430420.xml", "/workspace/datasets/product_data/products/products_0039_3691865_to_3781982.xml"]
    docs_indexed = 0
    tic = time.perf_counter()
    for file in files:
        logger.info(f'Processing file : {file}')
        tree = etree.parse(file)
        root = tree.getroot()
        children = root.findall("./product")
        docs = []
        for child in children:
            doc = {}
            for idx in range(0, len(mappings), 2):
                xpath_expr = mappings[idx]
                key = mappings[idx + 1]
                doc[key] = child.xpath(xpath_expr)
            # print(doc)
            if not 'productId' in doc or len(doc['productId']) == 0:
                continue

            #### Step 2.b: Create a valid OpenSearch Doc and bulk index 2000 docs at a time
            the_doc = doc.copy()

            # the_doc = {}
            # for x,y in doc.items():
            #     if isinstance(y, list):
            #         if y:
            #             y = ' '.join(y)
            #         else:
            #             y = ""
            #     the_doc[x] = y
            
            # the_doc['_id'] = the_doc.pop('productId')[0] #appears to generate wrong product total number, maybe replications?
            the_doc['_index'] = index_name

            docs.append(the_doc)

            docs_indexed += 1
            if len(docs) == 2000:
                bulk(client, docs)
                docs = []

        if len(docs) > 0:
            bulk(client, docs)

    toc = time.perf_counter()
    logger.info(f'Done. Total docs: {docs_indexed}.  Total time: {((toc - tic) / 60):0.3f} mins.')


if __name__ == "__main__":
    main()
