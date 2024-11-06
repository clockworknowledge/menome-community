

// match reasearch agent generated graph structure 
match p=(d:Document)-[]-(s:Step)-[:NEXT*..5]-(s2) where d.uuid='736ece2b-5bdd-4ab2-8127-7fc2f79fd6e3' with d,s,s2
optional match (s2)-[]-(d2:Document) where d2.type='Agent Contributed'
optional match (d2:Document)-[]-(p:Page)-[]-(c:Child)
optional match (p)-[]-(q:Question)
optional match (p)-[]-(su:Summary)
optional match (s2)-[]-(f:Feedback) 
return d,s,s2,d2,f,p,c,q,su 

// delete document graphs
MATCH (n:Document)-[]-(p:Page)-[]-(c:Child) where n.uuid='07def22f-2a6c-4b3f-9e5a-b2515fb87777' with  n, p, c
match (p)-[]-(q:Question)
match (p)-[]-(s:Summary)
detach delete n,p,c,q,s

// delete context nodes
MATCH (d:Document {uuid: '51e7722e-78f5-4737-a233-4b8257608430'})
WITH d
MATCH (d)-[:MENTIONS*1..3]-(n)
with distinct n
detach delete n


// Cleanup categories
// Remove __Community__ nodes
CALL apoc.periodic.iterate(
  "MATCH (c:__Community__) RETURN c",
  "DETACH DELETE c",
  {batchSize:1000}
);

// Remove Category nodes
CALL apoc.periodic.iterate(
  "MATCH (c:Category) RETURN c",
  "DETACH DELETE c",
  {batchSize:1000}
);


// Cleanup and remove specified research agent generated nodes includes file attachements
MATCH (d:Document ) where d.uuid='c1d515ee-1fde-4f90-b355-30f34f8fc603'
OPTIONAL MATCH (d)-[:HAS_WORKFLOW]->(st:Step)-[:NEXT*0..]->(st2:Step)
OPTIONAL MATCH (d)-[]->(p:Page)-[]->(c:Child)
OPTIONAL MATCH (p)-[]->(s:Summary)
OPTIONAL MATCH (p)-[]->(q:Question)
OPTIONAL MATCH (st2)-[:DESIGNED]->(d2:Document)
OPTIONAL MATCH (d2)-[]->(p2:Page)-[]->(c2:Child)
OPTIONAL MATCH (d2)-[]-(d3:Document)
OPTIONAL MATCH (d3)-[]-(p3:Page)-[]-(c3:Child)
OPTIONAL MATCH (p3)-[]-(q3:Question)
OPTIONAL MATCH (p3)-[]-(s3:Summary)
OPTIONAL MATCH (d)-[]-(ct:Category)
OPTIONAL MATCH (d)-[]-(f:File)
return   f,d, p, c, s, q, st, st2, d2, p2, c2, d3, p3, c3, q3,s3 ,ct


// Merge Category nodes
CALL apoc.periodic.iterate(
    "MATCH (c:Category)
     WITH c.name AS name, collect(c) AS nodes
     WHERE size(nodes) > 1
     RETURN nodes",
    "CALL apoc.refactor.mergeNodes(nodes, {
        properties: {
            uuid: 'discard',
            name: 'discard',
            description: 'discard',
            thelinkaddeddate: 'discard',
            '*': 'combine'
        }
     })
     YIELD node
     RETURN count(*)",
    {batchSize: 500}
)
YIELD batches, total, timeTaken, committedOperations
RETURN batches, total, timeTaken, committedOperations

// Cleanup and remove names that are not representative of a category
MATCH (c:Category)
WHERE c.name =~ '^[#\\$%\\(\\)\\+\\-\\./0-9].*' OR
      c.name =~ '.*[0-9].*' OR
      c.name =~ '.*[\\$%\\(\\)\\+\\-\\./].*' OR
      c.name =~ '.*[\\p{IsHan}\\p{IsHiragana}\\p{IsKatakana}\\p{IsCyrillic}\\p{IsArabic}\\p{IsHebrew}\\p{IsDevanagari}\\p{IsEthiopic}\\p{IsMyanmar}\\p{IsGreek}\\p{IsArmenian}\\u00C0-\\u00FF].*'
DETACH DELETE c
RETURN count(c) AS deletedCount



// Return Research Topic
// Step 1: Match Documents with the specified topic
MATCH (d:Document)
WHERE 'openai o1 model capabilities' IN d.topics

// Step 2: Traverse the workflow steps up to 5 NEXT relationships
OPTIONAL MATCH path = (d)-[:HAS_WORKFLOW]->(:Step)-[:NEXT*0..5]->(st:Step)

// Step 3: Find associated documents connected to the traversed steps
// Replace `RELATED_TO` with the actual relationship type if different
OPTIONAL MATCH (st)-[]->(associatedDoc:Document)

// Step 4: Combine initial and associated documents into a single collection
WITH path, collect(d) + collect(associatedDoc) AS allDocuments

// Step 5: Filter out any nulls from the combined documents
WITH [doc IN allDocuments WHERE doc IS NOT NULL] AS allDocuments, path

// Step 6: Match categories linked to the collected documents via the MENTIONS relationship
MATCH (c:Category)<-[:MENTIONS]-(doc:Document)
WHERE doc IN allDocuments

// Step 7: Collect distinct categories
WITH path, collect(DISTINCT c) AS categories, allDocuments

// Step 8: Unwind the documents to process each one individually
UNWIND allDocuments AS doc

// Step 9: For each document, find its Pages
OPTIONAL MATCH (doc)-[:HAS_PAGE]->(page:Page)

// Step 10: For each Page, find its Child, Question, and Summary nodes
OPTIONAL MATCH (page)-[:HAS_CHILD]->(child:Page)
OPTIONAL MATCH (page)-[:HAS_QUESTION]->(question:Question)
OPTIONAL MATCH (page)-[:HAS_SUMMARY]->(summary:Summary)

// Step 11: Collect Pages and their associated nodes per Document
WITH path, categories, doc, 
     collect(DISTINCT page) AS pages,
     collect(DISTINCT child) AS children,
     collect(DISTINCT question) AS questions,
     collect(DISTINCT summary) AS summaries

// Step 12: Aggregate the data into a structured format
WITH path, categories, collect({
    document: doc,
    pages: pages,
    children: children,
    questions: questions,
    summaries: summaries
}) AS documentDetails

// Step 13: Return the comprehensive data
RETURN path, categories, documentDetails


// Delete Research Document Graphs
// Return Research Topic
// Step 1: Match Documents with the specified topic
MATCH (d:Document)
WHERE 'openai o1 model capabilities' IN d.topics

// Step 2: Traverse the workflow steps up to 5 NEXT relationships
OPTIONAL MATCH path = (d)-[:HAS_WORKFLOW]->(:Step)-[:NEXT*0..5]->(st:Step)

// Step 3: Find associated documents connected to the traversed steps
// Replace `RELATED_TO` with the actual relationship type if different
OPTIONAL MATCH (st)-[]->(associatedDoc:Document)

// Step 4: Combine initial and associated documents into a single collection
WITH path, collect(d) + collect(associatedDoc) AS allDocuments

// Step 5: Filter out any nulls from the combined documents
WITH [doc IN allDocuments WHERE doc IS NOT NULL] AS allDocuments, path

// Step 6: Match categories linked to the collected documents via the MENTIONS relationship
MATCH (c:Category)<-[:MENTIONS]-(doc:Document)
WHERE doc IN allDocuments

// Step 7: Collect distinct categories
WITH path, collect(DISTINCT c) AS categories, allDocuments

// Step 8: Unwind the documents to process each one individually
UNWIND allDocuments AS doc

// Step 9: For each document, find its Pages
OPTIONAL MATCH (doc)-[:HAS_PAGE]->(page:Page)

// Step 10: For each Page, find its Child, Question, and Summary nodes
OPTIONAL MATCH (page)-[:HAS_CHILD]->(child:Page)
OPTIONAL MATCH (page)-[:HAS_QUESTION]->(question:Question)
OPTIONAL MATCH (page)-[:HAS_SUMMARY]->(summary:Summary)

// Step 11: Collect Pages and their associated nodes per Document
WITH path, categories, doc, 
     collect(DISTINCT page) AS pages,
     collect(DISTINCT child) AS children,
     collect(DISTINCT question) AS questions,
     collect(DISTINCT summary) AS summaries

// Step 12: Aggregate the data into a structured format
WITH path, categories, collect({
    document: doc,
    pages: pages,
    children: children,
    questions: questions,
    summaries: summaries
}) AS documentDetails

// Step 13: Return the comprehensive data

// Step 14: Detach and delete the collected nodes
WITH path, categories, documentDetails
UNWIND documentDetails AS detail
UNWIND detail.pages + detail.children + detail.questions + detail.summaries + [detail.document] AS nodeToDelete
DETACH DELETE nodeToDelete

// Step 15: Detach and delete the categories
WITH categories
UNWIND categories AS category
DETACH DELETE category


// Detach delete full topic resarch using path
// Step 1: Match the starting Step node and traverse up to 5 NEXT relationships
MATCH path = (d:Document {uuid:'2eba5ef8-64af-4a25-8350-5cb5ca96d80d')-[:HAS_WORKFLOW]-(s1:Step)-[:NEXT*0..5]->(st:Step)

// Step 2: Find associated documents connected to the traversed steps
OPTIONAL MATCH (st)-[]->(associatedDoc:Document)

// Step 3: Combine associated documents into a single collection
WITH path, collect(associatedDoc) AS allDocuments

// Step 4: Filter out any nulls from the combined documents
WITH [doc IN allDocuments WHERE doc IS NOT NULL] AS allDocuments, path

// Step 5: Match categories linked to the collected documents via the MENTIONS relationship
OPTIONAL MATCH (c:Category)<-[:MENTIONS]-(doc:Document)
WHERE doc IN allDocuments

// Step 6: Collect distinct categories
WITH path, collect(DISTINCT c) AS categories, allDocuments

// Step 7: Unwind the documents to process each one individually
UNWIND allDocuments AS doc

// Step 8: For each document, find its Pages
OPTIONAL MATCH (doc)-[:HAS_PAGE]->(page:Page)

// Step 9: For each Page, find its Child, Question, and Summary nodes
OPTIONAL MATCH (page)-[:HAS_CHILD]->(child:Page)
OPTIONAL MATCH (page)-[:HAS_QUESTION]->(question:Question)
OPTIONAL MATCH (page)-[:HAS_SUMMARY]->(summary:Summary)

// Step 10: Collect all nodes to delete
WITH 
    path, 
    categories, 
    collect(doc) AS docsToDelete,
    collect(DISTINCT page) AS pagesToDelete,
    collect(DISTINCT child) AS childrenToDelete,
    collect(DISTINCT question) AS questionsToDelete,
    collect(DISTINCT summary) AS summariesToDelete

// Step 11: Collect all Step nodes in the path
WITH 
    path, 
    categories, 
    docsToDelete, 
    pagesToDelete, 
    childrenToDelete, 
    questionsToDelete, 
    summariesToDelete,
    nodes(path) AS stepsToDelete

// Step 12: Combine all nodes to delete into a single list
WITH 
    stepsToDelete + 
    docsToDelete + 
    pagesToDelete + 
    childrenToDelete + 
    questionsToDelete + 
    summariesToDelete + 
    categories AS nodesToDelete

// Step 13: Remove any nulls from the combined list
WITH [n IN nodesToDelete WHERE n IS NOT NULL] AS nodesToDelete

// Step 14: Detach delete all collected nodes
UNWIND nodesToDelete AS n
DETACH DELETE n
