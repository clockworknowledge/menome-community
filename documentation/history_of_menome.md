# clockworKnowledge - Menome Platform

The quest for the ability to  capture and curate Knowledge started when I become involved in a project called Amine. 
 
The Amine system was designed to be a 3 dimensional mine modeling system that was made up of a number of modules geared towards underground mine planning and design. The core of this system was a drawing manager that represented mine objects in a common fashion, and a programming framework that allowed for modular construction. 
 
The leader of the Amine project had an interesting view of what that project was about.  He believed that the real challenge was not the 3d modeling, numerical analysis or any other technical discipline relating to the visible 3d outputs – he felt all of these could and would be solved. The challenge was organizing and managing documents and knowledge artifacts that made up the model– this problem, he felt , would be a challenge that would last for decades. 
 
The question always was – how do you know what is ‘Quality’ Knowledge? This lead me to start looking for a way to create a system for managing Knowledge based on a ‘Knowledge Quality’ rank. 
 
While google’s page rank has been applied to addressing this question on the web, the issue for enterprises is that page rank does not work well. This is due to the fact that the knowledge inside an enterprise is not linked, is stored in much more diverse formats, and also has to factor in the human context and also the feedback ‘copy/past/extend/augment’ element. 
 
The complexity of managing and organizing Knowledge is subtle but as it turns out was beyond the complexity of any numerical model. This is because the classification and organization of knowledge is a pure abstraction – each person using knowledge will have a different view of what makes up ‘Quality’ knowledge, and will have a different way of structuring, classifying, organizing and selecting that knowledge that is relevant to them and their current context. People also don’t store the resulting knowledge assets in a manner that makes it amenable to discovery. 
 
The larger an organization becomes, the larger the problem becomes. 
 
We need therefore to come up with a different strategy for creating the ‘Recommendation’ algorithm that will help validate knowledge. The original Menome ‘ranking’ concept may provide a starting point for this...
 
## The ‘Menome’ Knowledge Rank.....
 
An enterprise provides a specialized environment in which certain types of knowledge will evolve based on the nature of the business that that enterprise operates in. The nature of this environment will change over time as the organization changes in response to external business conditions imposed on it. 
 
The notion of Quality in the natural environment is not static - it changes over time. An organism can be considered to be ‘high quality’ in one environment because it has specialized characteristics that give it the ability to survive and reproduce in that environment. These characteristics might not be of high quality in a different environment, and so the organism will die out if placed into an environment not suited to its characteristics.
 
By the same token, knowledge of ‘high quality’ in relation to an knowledge environment it thrives in will not successfully propagate if it is not of ‘high quality’ in a different environment. 

A Knowledge Asset is any piece of knowledge or information that has value and can be shared, used, and reused independently. It can be a fact, concept, process, procedure, or any other piece of information that is deemed useful and relevant for a particular purpose or context.

Natural selection and thus evolution of Knowledge Assets in a given Knowledge environment is driven by people selecting which Knowledge Assets will survive and which will not given the person’s current context. 
 
Knowledge that is useful will survive to replicate  within the information environment provided by that organization and the employees who are the organization’s ‘natural knowledge selectors’. 
 
In order to trace the evolution of Knowledge in an organization, all Knowledge in the environment must be decomposed into ‘Knowledge Assets’.
 
These Knowledge Assets can then be traced as they evolve through applying similarity ranking algorithms to link the Knowledge Assets together. 
 
Linking these  Knowledge Assets into a graph provides the foundation with which ‘Knowledge Dimensions’ can be computed which will form the basis of the menome ranking algorithm. Analyzing the evolutionary patterns and the rate of change of the ‘menome’ as the Knowledge Graph evolves through ‘naturally selection’ driven by people in organizations provides a signal as to the relative quality of the Knowledge Asset. 
 
The quality rank must factor in in context of the person seeking knowledge through their dimensional lens. 
 
The menome Platform seeks to capture and organize Knowledge Assets as they propagate through an organization and display them in context relevant to the person looking at them using the menome algorithm. 
 
The Knowledge Assets can be manipulated, filtered, sliced, visualized, augmented and annotated using organizational dimensions on the knowledge Canvas. 
 
## Computing the 'Menome' of a Knowledge Asset
 
By not using a single indexing method, but rather using a combination of the distinguishing dimensions of an Knowledge Asset, a ranking system can be established based on the distance between these dimensions. 
 
This similarity rank can then be used to plot the information asset on a Canvas style view, which gives a graphical representation of how the Knowledge Assets are related to teach other. Other views of single dimensions involved in the rank can also be used to further refine the bounds of the ranking.  
 
Potential Primary Features are:
	· Time - Timeline view in which information assets are laid out along a linear time scale
	· Spatial or Map view - View in which information assets are plotted on a map based on association with their work product location
	· Social - view of status updates with respect to collaborators in the corporation
	· Status - Ranked on current status of the asset or collaborator
	· Rate of knowledge evolution - how fast a Knowledge Asset is evolving and propagating through a Knowledge Environment 
	· Environment pressure - how much pressure the business environment is putting on documents
	· Natural Selector - which employees are driving the process of natural selection of Knowledge Assets
	 
## Knowledge Evolution 'Velocity ':
 
A corporation defines the boundaries of an 'Knowledge Environment'. Knowledge that is of use to the corporation's survival as a 'viable entity' will survive, be reproduced and evolve. The driver of Knowledge Evolution inside a corporation are its employees, who naturally select the Knowledge that is relevant to them at that time. This concept defines what amounts to a 'Knowledge Graph' that factors in evolution of knowledge assets. Knowledge existing in the Knowledge Graph is linked by dimensions that relate to the company's business. Each Knowledge Asset has its own position in this environment.
 
Every evolutionary history of an Knowledge Asset consists of a particular pathway through this graph. The position of the Knowledge Asset is fixed in this Knowledge Graph by its dimensional properties. Evolutionary change consists of a step by step walk through this graph as driven by the employees of the company who naturally select and classify the Knowledge. Therefore the amount of 'distance' between two Knowledge Elements can be computed based on the dimensional differences. This can be thought of as a 'Menome Rank', which can be applied to generating a ranking index for knowledge assets. 
 
By measuring how fast related Knowledge changes (i.e. combination of menome distance and time between related Knowledge elements) it may be possible to further improve the ranking system. Things that are evolving quickly are likely to be of more relevance that information elements that are static. 
 
In order to do this, it is necessary to create the ‘web’ of enterprise knowledge by combining all available structured and unstructured sources inside an enterprise. This system must be capable of continuously harvesting, refining and integrating knowledge from any type of structured and unstructured source into this ‘web’  must be created – a ‘datalink’ system. 

## theLink - Refacorting the Menome datalink to leverage LLMs

The Menome Datalink product was a mulit-agent system that was capable of continously harvesting and integrating data from any structured or unstructured source into a knowledge graph, and making it availble to people to interact with to answer questions etc. 

While the data atomization-> graph pattern aspect of the platform was successful, and worked well, the Q/A and navigation through the graph was not. We were not able to effectively transform user questions into useful results due to limits of technology at the time. Various NLP methods, including LDA, LSI, and others were tried, but none of them were able to provide the results we needed.

The advent of large language models effectively solves this challenge. It is now possible to combine the power of the knowledge graph patterns, the data integration pattern and then layer the capabilities of LLMs in to make a truely powerful dynamic knowledge repository. 

This project seeks to refactor the base Menome datalink platform using latest methods with the addition of large languagel model capabilities. 

The approach is starting with simplifying the datalink pattern down to basics, building a basic simple FASTapi using python, and then expand from that foundation. 

It may be possible to harness some of the processing agents created during the Menome datalink development, but this is not a priority at this time. Its likely that AutoGEN or equivalent may be the way to handle some of the data integration aspects.

## Baseline Features and Ideas:

1. User Authentication, login and session management
2. Ability to contribute documents from URLs
3. Processing of documents into chunks
4. Basic chat capabiltiy for document q/a 
5. Basic search capability
6. Basic document recommendation capability
7. Basic document similarity capability
8. Basic document clustering capability
9. Basic document summarization capability
10. Basic document tagging capability
11. Basic document annotation capability
12. Inroducting the concept of "Knowledge Clips" - user clipping and annotation of Knowledge Assets 
13. Assembly of Knowledge Clips into new Knowledge Assets
14. Entity extraction from incoming content, and promotion of entity to a knowledge asset
15. Extending knowledge about a new knowledge asset

## Architecture

Initially the system will use a simple FASTapi backend with a Neo4j database. Neo4j Aura Free can be used for the initial development and/or neo4j desktop with a local instance. The system does require neo4j 5.11 or better as this version is the one that supports the new vector indexing features.

The system will use the new Neo4j vector indexing features to store the embeddings from the LLMs. The UX will be constructed using generative AI methods, and will be a web based application initially. Additional plug ins or projections into other environements and front ends will be added over time.

### Data Model

The data model is based on the Menome Knowledge Graph model, but simplified right down to basics as the approach to developing a knowledge system has evolved considerably since the original Menome datalink was developed.

The base model will start with simple concept of Users, Content specifically Documents, Knowledge Assets/Chunks and Knowledge Clips. This will be extended to include other graph document structures such as Files->Pages->Chunks as the system evolves.

### Knowledge Asset 

A Knowledge Asset, in the context of contemporary advancements, is a discrete unit of knowledge that holds significant value within a specific context or environment. Knowledge Assets are meticulously curated and validated by domain experts to ensure their accuracy and relevance to the specific domain under consideration.

In today's technological landscape, Knowledge Assets play a pivotal role in training and validating large language models. These models rely on Knowledge Assets and Knowledge Graphs, which represent agreed-upon facts and relationships, to enhance their ability to provide accurate and contextually relevant responses to questions and inquiries. These Knowledge Assets serve as the foundational bedrock upon which these models are built.

Furthermore, the integration of "Real Human Feedback in the Loop" has become a crucial component of refining and validating large language models. Human feedback mechanisms involve continuous interactions between human experts and the models, where experts evaluate the responses generated by the models for correctness and context appropriateness. This feedback loop not only helps in fine-tuning the models but also in identifying and rectifying potential biases and inaccuracies that may arise during model training.

In essence, Knowledge Assets, Knowledge Graphs, and Real Human Feedback in the Loop work in concert to ensure that large language models are equipped with accurate and contextually relevant knowledge, enabling them to excel in tasks like question-answering, problem-solving, and decision-making within specific domains. These advancements represent a critical step toward harnessing the full potential of artificial intelligence to support organizations in achieving their objectives.

Here are key attributes and functionalities of a Knowledge Asset within the described knowledge management framework:

Capture and Curation:

Originating from a quest to manage and organize knowledge effectively, Knowledge Assets are captured and curated within a system designed to model and structure these assets in a meaningful manner.
Quality Assessment:

The concept of 'Knowledge Quality' is central to determining the value and relevance of a Knowledge Asset. A specialized ranking or recommendation algorithm, inspired by the Menome Knowledge Rank, evaluates the quality based on various dimensions including the asset's evolution, utilization, and contextual relevance within the organization.
Evolution and Natural Selection:

Knowledge Assets evolve over time through a process likened to natural selection, where employees within an organization act as 'natural knowledge selectors'. They choose, utilize, and propagate knowledge based on its relevance and usefulness to their current tasks and broader organizational goals.
Knowledge Graph and Menome Rank:

The interlinking of Knowledge Assets into a knowledge graph, assessed through a Menome Rank, helps trace the evolutionary pathways and quality ranking of these assets. This rank, computed based on distinguishing dimensions and the relative 'distance' between assets in the knowledge graph, provides a structured approach to evaluating and organizing knowledge.
Visualization and Manipulation:

Knowledge Assets can be visualized, manipulated, and annotated on a knowledge Canvas, aiding in better understanding, filtering, and utilization. Various views and dimensions, including time, spatial, social, and status, provide multiple lenses through which assets can be evaluated and related to each other.
Knowledge Evolution 'Velocity':

By measuring the rate of change or evolution of related Knowledge Assets over time, insights into their relevance and potential value can be garnered. Fast-evolving assets might indicate higher relevance and utility within the current organizational context.
Continuous Harvesting and Integration:

A systematic approach to continuously harvesting, refining, and integrating knowledge from diverse sources into the knowledge graph ensures a dynamic, up-to-date repository of Knowledge Assets. This 'datalink' system acts as a nexus for aggregating and organizing enterprise knowledge.
Contextual Relevance:

The Menome platform aims to present Knowledge Assets in a context relevant to the individual user, enhancing the personalized utility and understanding of the knowledge within the organizational milieu.
Collaboration and Sharing:

The framework fosters collaboration and sharing among employees, enriching the collective knowledge base and facilitating a culture of collective intelligence and continuous learning.


### Trail 
The concept of a Trail is based on the Associative Trail derived from Vannevar Bush Document As We May Think. 

In "As We May Think," Vannevar Bush introduces the concept of the "associative trail," where individuals can traverse a trail of thought or information by following links from one item to another based on associations, much like how the mind works. This idea predates and arguably inspired the development of hypertext and the World Wide Web.

In the scenario you provided, a dynamic knowledge graph model serves as a structured representation of documents and concepts, defined as Knowledge Assets. These assets are interconnected through various types of relationships or associations, much like nodes and edges in a graph.

1. **Exploration:** As users explore this knowledge graph, they navigate from one Knowledge Asset to another along the associative trails formed by these relationships. Their journey can be driven by inquiry, interest, or the pursuit of understanding, akin to following a trail of thought.

2. **Assembly of Knowledge Clips:** While traversing, users can collect or mark certain Knowledge Assets, forming "Knowledge Clips". These clips are essentially sub-graphs or segments of the larger knowledge graph that are deemed relevant to the user's line of inquiry. This is a modern digital rendition of Bush's vision where individuals could create and follow associative trails to manage and explore information.

3. **Creation of New Content:** The assembled Knowledge Clips serve as a foundation for creating new content. Whether it be documents, documents, or presentations, these clips provide a structured, contextual basis from which users can synthesize and build new knowledge. The trails essentially act as a scaffold, organizing information in a way that mirrors natural human cognition and associative reasoning.

4. **Extensibility:** Moreover, the dynamic nature of the knowledge graph allows for the continuous addition and modification of Knowledge Assets and associations. This fluidity ensures that as new knowledge is generated, it can be seamlessly integrated into the existing graph, thereby extending the associative trails and enriching the exploration experience.

5. **Collaboration:** Furthermore, in a collaborative environment, the trails created by individuals could be shared, extended, or merged with others. This collaborative exploration and creation of associative trails promote collective intelligence and knowledge sharing.

6. **Documentation and Reuse:** The trails, once documented, can be revisited or reused either by the original user or others in the community. This promotes efficiency and the cumulative growth of knowledge over time.

By implementing an associative trail model within a dynamic knowledge graph, the process of inquiry, exploration, and creation becomes a structured yet flexible process, mirroring the organic way in which individuals think, learn, and collaborate. This model facilitates not only personal knowledge management but also collective intelligence and the continuous expansion and refinement of the shared knowledge base.

### Knowledge Clip

A Knowledge Clip, as described, is a specialized form of a Knowledge Asset specifically flagged by a user due to its relevance to their ongoing content creation task within a dynamic knowledge graph. Here's a breakdown of its concept and functionality:

1. **Identification and Selection:** 
   - A Knowledge Clip emerges when a user identifies a particular Knowledge Asset (or a collection thereof) as beneficial for their current task. This selection process is user-driven and is based on the perceived value or relevance of the asset in aiding the content creation process.

2. **Annotation:** 
   - Post selection, users have the option to annotate the Knowledge Clip. Annotations can include additional context, personal insights, references, or any other information the user deems necessary. This feature enhances the personalized understanding and relevance of the Knowledge Clip, making it a richer resource for the user.

3. **Integration:** 
   - The Knowledge Clip, now augmented with user annotations, becomes an integral part of the user's content creation workflow. It can be referenced, cited, or even directly incorporated into the new content being created, acting as a building block in the assembly of new knowledge.

4. **Interconnection:** 
   - Within the knowledge graph, Knowledge Clips maintain their associative connections to other Knowledge Assets. This allows for an easy expansion or exploration of related concepts, aiding in a more comprehensive understanding and utilization of the information at hand.

5. **Reuse and Evolution:** 
   - Knowledge Clips are not static; they can be revisited, re-annotated, or expanded upon in future tasks. They may evolve over time with additional annotations or as new related Knowledge Assets are added to the knowledge graph.

6. **Collaboration and Sharing:** 
   - In a collaborative environment, Knowledge Clips could be shared among users, allowing for collective input, annotations, and utilization. They can serve as communal knowledge building blocks, fostering a collaborative knowledge creation and sharing culture.

7. **Traceability:** 
   - The annotations and the trail of Knowledge Clips provide a traceable path of the user's thought process and research journey. This traceability is valuable for both personal reflection and external validation of the created content.

8. **Enhanced Content Creation:** 
   - By organizing and annotating key pieces of information as Knowledge Clips, users can streamline their content creation process, ensuring that valuable insights and information are easily accessible and effectively utilized.

A Knowledge Clip is a user-curated and potentially annotated Knowledge Asset that plays a crucial role in the user’s content creation endeavor, bridging the gap between information exploration and knowledge synthesis in a structured and personalized manner.


## Content Types:

Content types are published documents, documents or artifacts that have been published by an author or creator. These are typically in a final, finished form. 

### Document Knowledge Assets: 

Documents are a form of Published Content that is produced by Authors on a subject for a purpose. This basic structure acts as a 'backbone' for other content processes that would seek to extract additional useful information from the Knowledge Asset and generate new nodes from them. These might inclued : Named Entities such as authors, publishing dates, categories or keywords, places etc. 

(a:Document)-[:HAS_PAGE]->(p:Page)-[:HAS_CHILD]->(c:Child)


Document: 
* uuid: unique identifier for node
* name: name of document
* url: url of source
* text: full text of source 
* note: a note about the source
* imageurl: URL of image for source
* publisher: publisher of source
* addeddate: date item was added
* thumbnail: thumbnail image for source
* wordcount: count of number of words in text
* type: "Document"

Page: 
* uuid - unique identifier
* name - name of page computed from processing (Page 1... Page N)
* source - used for getting source nodes from RAG query pattern
* text - page text
* embedding - text embedding for similarity search


Child:
* uuid - unique identifier for chunk
* name - name of chunk if available
* embedding - embedding vector of chunk from OpenAI
* text - full text of chunk 
* source - uuid of document associated with chunk for secondary query


Summary: 
(p:Page)-[:HAS_SUMMARY]->(s:Summary)
* "uuid": unique identifier for summary,
* "text": summary text from LLM,
* "embedding": text embedding for similarity search
* datecreated: date summary was created

Question:
(p:Page)-[:HAS_QUESTION]->(q:Question)
* "text": question text result from LLM, 
* "uuid": unique identifier for question, 
* "name": f"{i+1}-{iq+1}", 
* "embedding": text embedding for similarity search


