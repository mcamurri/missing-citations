from math import ceil

# To parse the stuff in Google Scholar
from serpapi import GoogleSearch

# To get a DOI given a title
from crossref_commons.iteration import iterate_publications_as_json

# To parse the stuff in Scopus
from pybliometrics.scopus import AuthorRetrieval
from pybliometrics.scopus import ScopusSearch
from pybliometrics.scopus import AbstractRetrieval
from pybliometrics.scopus import AuthorSearch
from scholarly import MaxTriesExceededException

# To pretty print and store into yaml file
import yaml
import json

from scholarly import scholarly
from scholarly import ProxyGenerator

def getScopusLinkFromDoi(doi):
  search_document = ScopusSearch('DOI(' + doi + ')')
  if search_document.get_results_size() == 0:
    return ''
  eid = search_document.get_eids()[0]  
  search_details = AbstractRetrieval(eid)

  return search_details.scopus_link

def getScopusAuthorIdFromOrcid(my_orcid):
  search_me = AuthorSearch('ORCID('+ my_orcid + ')')
  my_eid = search_me.authors[0].eid
  print('EID for ORCID' + my_orcid + ': ' + my_eid)
  me = AuthorRetrieval(my_eid)  
  print(me)
  return str(me.identifier)

def getScholarDocumentsFromScholarly(author_id, doi_cache, use_proxy=False):
  if use_proxy:
    # Set up a ProxyGenerator object to use free proxies
    # This needs to be done only once per session
    pg = ProxyGenerator()
    pg.FreeProxies()
    scholarly.use_proxy(pg)
    
  # Retrieve the author's data, fill-in, and print
  # Get an iterator for the author results
  scholar_me = scholarly.search_author_id(author_id)
  # Retrieve the first result from the iterator


  # Retrieve all the details for the author
  scholarly.fill(scholar_me, ['publications'])  
  
  
  articles = scholar_me['publications']

  # Print the titles of the author's publications
  #publication_titles = [pub['bib']['title'] for pub in author['publications']]
  #print(publication_titles)


  scholar_documents = {}

  publications_without_doi = []
  try: 
    for p in articles:
      pp = p['bib']
      scholar_title = pp['title']
      print('Title: ' + scholar_title)  
      doi = getDoiFromTitle(scholar_title, doi_cache)
      if doi == '':
        print('Publication not found: ' + scholar_title)
        publications_without_doi.append(scholar_title)
        continue
      else:
        print('DOI: ' + doi)
    
      num_citations = p['num_citations']
      print('Citations: ' + str(num_citations))
      if num_citations == 0:
        print('Skipping publication ' + doi + ' because it has no citations.')
        continue
    
      cite_id = p['cites_id']
      citations = {}
      scholar_documents[doi] = {'title' : scholar_title,
                                'citations' : citations}
      try:
        scholar_citations = scholarly.citedby(p)    
        i = 1    
        for sc in scholar_citations: 
          citation_title= str(sc['bib']['title'])
          citation_doi = getDoiFromTitle(citation_title, doi_cache)
           
          print(' '+ str(i) + ') ' + citation_doi + '  ' + citation_title)
          i += 1
          if citation_doi != '':            
            scholar_documents[doi]['citations'][citation_doi] = citation_title
      except MaxTriesExceededException:
        print('Captured MaxTriesExceededException. Please try again later or use different proxy.')
        print('WARNING: Citations for document ' + doi + ' might be incomplete (' + len(citations) + ' vs ' + num_citations + ').')        
        continue      
  except:
    pass
  return scholar_documents

def getScopusDocumentsFromScopus(my_orcid):
  my_author_id = getScopusAuthorIdFromOrcid(my_orcid)
 
  # Get all document from me
  s = ScopusSearch('AU-ID('+ my_author_id + ')')
  eids = s.get_eids()
  
  # Make a container with all my papers and their citations
  scopus_documents = {}
  
  s = 1
  # Iterate over my papers
  for eid in eids:
    # Retrieve info about title and DOI of a paper given the eid
    doc = AbstractRetrieval(eid)

    print(str(s) + ') ' + eid + ' doi: ' + doc.doi + ' Title: ' + doc.title + ' ')
  
    # Get all papers that cite my paper
    citedby = ScopusSearch('REF(' + eid + ')')
    citations = {}
  
    # For each one of the papers that cite my paper, get title and doi
    for c in citedby.get_eids():
      citation = AbstractRetrieval(c)
      citations[citation.doi] = citation.title
    
    # Store citations and titel of my paper into the container
    scopus_documents[doc.doi] = {'title' : doc.title,
                                 'citations' : citations}
  return scopus_documents

def getScholarDocumentsFromFile(filename='scholar_documents.json'):
  f = open(filename, "r", encoding="utf-8")
  scholar_documents = json.load(f)
  f.close()
  return scholar_documents

def getScopusDocumentsFromFile(filename='scopus_documents.json'):
  scopus_documents_file = open(filename, "r", encoding="utf-8")
  scopus_documents = json.load(scopus_documents_file)
  scopus_documents_file.close()
  return scopus_documents

#my_orcid = '0000-0003-2675-9421'
##print(scopus_documents)
## print(yaml.dump(scopus_documents, allow_unicode=True, default_flow_style=False))
#
#
#f = open("scopus_documents.json", "w", encoding="utf-8")
#json.dump(scopus_documents, f)
#f.close()

def loadDoiCache():
  try:
    doi_cache_file = open('doi_cache.json', 'r', encoding='utf-8')
    doi_cache = json.load(doi_cache_file)
    doi_cache_file.close()
  except FileNotFoundError:
    doi_cache = {}
  return doi_cache

def storeDoiCache(doi_cache):
  doi_cache_file = open('doi_cache.json', 'w+', encoding='utf-8')
  json.dump(doi_cache, doi_cache_file)
  doi_cache_file.close()

def getDoiFromTitle(title, cache=None):
  if cache == None:
    cache = {}
  if title in cache.keys():
    return cache[title]
  
  # for each publication, store the title into a query request
  queries = {'query.title': title}
  # query crossref to get the DOI corresponding to the title
  
  crossref_title = ''
  try:
    item = next(iterate_publications_as_json(max_results=1, queries=queries))
    crossref_title = str(item['title'][0])
  except KeyError:
    print('Title ' + title + ' not found on Crossref')    
  except ConnectionError:
    print('Could not connect to Crossref')

  # if crossref fails, attempt Scopus
  #if crossref_title == '':


  

  crossref_title_lower = crossref_title.lower()
  res = ''
  # if the crossref title and the provided title are not the same, DOI is not valid
  if(title.lower() ==  crossref_title_lower):
    res = str(item['DOI'])
  return res
  
def getScholarDocumentsFromSerpApi(author_id, api_key, doi_cache) :

  params = {
    "engine": "google_scholar_author",
    "author_id": author_id,
    "api_key": api_key
  }

  search = GoogleSearch(params)
  results = search.get_dict()
  # Find all articles from the given author
  articles = results['articles']

  scholar_documents = {}
  # For each article extract title, DOI, and num of citations
  for p in articles:
    scholar_title = p['title']
    doi = getDoiFromTitle(scholar_title, doi_cache)
    if doi == '':
      print('Article ' + scholar_title + ' has no DOI')
      continue
    num_citations = p['cited_by']['value']
    if num_citations == 0:
      print('Article ' + scholar_title + ' with DOI ' + doi + ' has no citations.')
      continue
    # if the article has been cited, we save the results
    cite_ids = p['cited_by']['cites_id'].split(',')
    print('There are ' + str(len(cite_ids)) + ' cite_ids associated to this article')
    citations = {}
    # store empty citations for now
    scholar_documents[doi] = {'title' : scholar_title,
                            'citations': citations}
    grandtotal_results = 0
    # each article can have one or more cite_id. If we make a search for each one of the cite_ids, 
    # we should get all the citations
    for cite_id in cite_ids:
      # start with the first page of citations. The biggest page we can get is 20
      article_params = {
          "engine": "google_scholar",
          "cites": cite_id,
          "api_key": api_key,
          "start" : "0",
          "num" : "20"
        }
      citations_search = GoogleSearch(article_params)
      citation_results = citations_search.get_dict()
      # total results is the total number of citation for the given cite_id
      total_results = 0
      try:
        total_results = citation_results['search_information']['total_results']
      except KeyError:
        pass
      print('There are ' + str(total_results) + ' total results for cite_id '+ cite_id)
      if total_results == 0:
        continue
      # update the total number of results for all cite_ids. It should become
      # identical to the total number of citations
      grandtotal_results += total_results
      organic_results = citation_results["organic_results"]
      # fill in the data for the first page  
      for res in organic_results:
        citation_title = res['title']
        citation_doi = getDoiFromTitle(citation_title, doi_cache)
        if citation_doi == '':
          print('Article \'' + citation_title + '\' citing article \'' + scholar_title + '\' with DOI ' + doi + ' has no DOI')
          continue
        scholar_documents[doi]['citations'][citation_doi] = citation_title

      # now that we know how many results there will be for this cite_id, we can calculate
      # the number of pages
      pages = ceil(total_results / 20)
      print('There are ' + str(pages) + ' pages for these results')
      # skip the first page as we processed it above
      for page in range(1, pages):
        print('Processing page ' + str(page) + '...')
        # the only search parameter we change is what page we are going to read
        article_params['start'] = str(page * 20)
        citations_search = GoogleSearch(article_params)
        citation_results = citations_search.get_dict()        
        organic_results = citation_results["organic_results"]
        # Process the results for this page
        for res in organic_results:
          citation_title = res['title']
          citation_doi = getDoiFromTitle(citation_title, doi_cache)
          if citation_doi == '':
            print('Article \'' + citation_title + '\' citing article \'' + scholar_title + '\' with DOI ' + doi + ' has no DOI')
            continue
          scholar_documents[doi]['citations'][citation_doi] = citation_title
    if(grandtotal_results != num_citations):
      print('WARNING: total number of results differs from num citations: ' + grandtotal_results + ' != ' + num_citations) 
    # fill in the scholar documents for each document by the author
  return scholar_documents

author_id = '_yTpZ7QAAAAJ'
api_key = '5e5ad9946d302bbc3d5210309b22254e0a831280112e18cf27adb0dc1118434f' # marco.camurri.phd@gmail.com
api_key = 'e58357382b30f0c238c3ffc5a46f888c90dc9d1f0e0b229b95470fa7dbb0f914' # shark04@gmail.com
api_key = '60f531c8987a1f0d16eb06247797c746911e54b903736b7cd49cd6d482e399b8' # mcamurri@oxfordrobotics.institute
orcid = '0000-0003-2675-9421'

doi_cache = loadDoiCache()

scopus_documents = getScopusDocumentsFromScopus(orcid)
# scopus_documents = getScopusDocumentsFromFile()
# scholar_documents = getScholarDocumentsFromScholarly(author_id, doi_cache, True)
# scholar_documents = getScholarDocumentsFromSerpApi(author_id, api_key, doi_cache)
# scholar_documents = getScholarDocumentsFromFile()

# storeDoiCache()

# print('Scholar Articles: ')
# print(scholar_documents)
# print('////////////////////////////////////////////////////////////////////////////////////')
# print('Scopus Articles:')
# print(scopus_documents)
# print('////////////////////////////////////////////////////////////////////////////////////')

# missing_citations = []

# for scholar_doi in scholar_documents:
#   # if the document does not exist in scopus we report
#   if not scholar_doi in scopus_documents.keys():
#     print('------------------------------------------------------------------------------------')
#     print('Document: ' + scholar_doi + ' not present in Scopus')
#     print('------------------------------------------------------------------------------------')
#     print('Title: ' + scholar_documents[scholar_doi]['title'])
#     print('DOI: ' + scholar_doi)
#     print('')
#     continue

#   # traverse all citations for the given document
#   for citation_doi in scholar_documents[scholar_doi]['citations']:
#     # if the citation is not present, we report the missing citation
#     if not citation_doi in scopus_documents[scholar_doi]['citations']:
#       print('------------------------------------------------------------------------------------')
#       print('Citation: ' + citation_doi + ' for article ' + scholar_doi + ' not present in Scopus')
#       print('------------------------------------------------------------------------------------')
#       cited_title = scholar_documents[scholar_doi]['title']
#       cited_link = getScopusLinkFromDoi(scholar_doi)
#       citing_title = scholar_documents[scholar_doi]['citations'][citation_doi]
#       citing_link = getScopusLinkFromDoi(citation_doi)
#       missing_citations.append({'cited_article' : cited_title,
#                                  'cited_link' : cited_link,
#                                  'citing_article' : citing_title,
#                                  'citing_link' : citing_link})
#       print('Cited article title: ' + cited_title)
#       print('Cited article link in Scopus: ' + cited_link)
#       print('Citing article: ' + citing_title)
#       print('Citing article link in Scopus: ' + citing_link)
#       print('')
#       continue
# missing_citations_file = open('missing_citations.yaml', "w+", encoding="utf-8")
# yaml.dump(missing_citations, missing_citations_file)
# missing_citations_file.close()

# scholar_documents_save = open('scholar_documents.json', 'w+', encoding="utf-8")
# json.dump(scholar_documents, scholar_documents_save)
# scholar_documents_save.close()