# Milestone 3 (30%)

**Faculty of Media Engineering and Technology — German University in Cairo (GUC)**  
**Instructor:** Dr. Nourhan Ehab  
**Deadline:** 10th of December at 23:59

---

## Overview

Build an end-to-end **Graph-RAG Formula 1 assistant** that uses the Neo4j Knowledge Graph from Milestone 2 as a grounding mechanism for an LLM-based system. Your system must retrieve the relevant nodes and relationships from the knowledge graph, then use those results to guide the LLM's final answer. The same assistant also runs the podium-prediction model from Milestone 1 and explains that prediction in plain language.

The assistant has two capabilities:

1. **Grounded question answering:** The user asks a question such as *"How many wins did Hamilton have at Silverstone before 2020?"* The system classifies the intent, extracts the entities, runs the matching Cypher query, and passes only the retrieved results to the language model.
2. **Prediction explainer:** The user either asks the chat about a driver, which opens the prediction view with the extracted details pre-filled, or enters the pre-race features directly. The saved Milestone 1 model predicts whether that driver finishes on the podium. A language model then explains the result from the live SHAP/LIME output and, when they are available, from supporting facts in the knowledge graph.

The project highlights how **symbolic reasoning** (the knowledge graph) and **statistical reasoning** (the podium model and the language model) collaborate to reduce hallucination, increase factual accuracy, and enhance interpretability. The knowledge graph and the podium model supply the facts. The language model only turns those facts into sentences.

> **Important constraints:** You **CANNOT** rename or remove any label or relationship already in the Milestone 2 schema. If your pre-race features need data that is not in that schema (for example standings), do not extend the graph for it: compute those features from the Milestone 1 CSVs with the same leakage rules as Milestone 1. Do not retrain the podium model inside the application. Load the saved model and its preprocessing from file.

---

## System Requirements

### 1. Input Preprocessing

#### a. Intent Classification
Classify what the user wants to ask, so the message can be routed to the right Cypher template. Implement **two approaches** and compare them on the same label set:

* **Rule-based classification:** keyword and pattern matching, including paraphrase patterns, so a reworded question still maps to one of your predefined question types.
* **Neural approach:** implement one of the following:
  * **Embedding similarity:** embed the example phrasings of each intent once, then assign the message to the nearest intent by cosine similarity. Use a minimum score and a margin: if the best score is below the minimum, or too close to the second-best intent, ask the user to rephrase instead of guessing. Choose an appropriate embedding model.
  * **LLM intent classification:** prompt a language model with your intent labels, a short description of each, and a few example phrasings, and have it return exactly one label from that list. If the output is not one of your labels, or the model indicates it is unsure, ask the user to rephrase instead of guessing.

**Additional requirements:**
* **Handle follow-ups:** a follow-up that does not name a new intent keeps the cached intent. A message must not be marked out of scope by similarity alone in the case of embedding similarity.
* **Evaluation set:** build a labelled set of at least **50 questions**, at least 4 per intent, including out-of-scope questions. Phrase them differently from the examples used to build the classifiers. Report accuracy and a confusion matrix for each approach, and justify which one you deploy.
* **Intent set:** your question types from Section 2, plus an out-of-scope intent and a podium-prediction intent.

#### b. Entity Extraction
Extract the entities needed by the chosen template. These are the values passed into the Cypher query. Entity types: **drivers**, **constructors**, **circuits**, **races** (by Grand Prix name and year), and **seasons or year ranges**.

* Accept a full name or surname, a constructor short name or compact alias (for example `"redbull"` or `"mercedes amg"`), and a circuit name or city.
* If a required entity is missing, or a name matches more than one driver (e.g., `"Schumacher"`), ask the user instead of guessing.
* **Entity cache:** keep an entity cache for the session. Store the last identified entities. A follow-up reuses that cache and replaces only the slot the new message names:
  * *"And in 2020?"* keeps the driver or team and replaces the season.
  * *"What about Norris?"* keeps the season and replaces the driver.
  * *"2021?"* and *"How many points did he score in 2019?"* reuse the cached driver.
  * An out-of-domain question does not clear the cache.
  * Show the cache in the interface so a follow-up is traceable.

---

### 2. Graph Retrieval Layer

The retrieval layer is a library of parameterised Cypher templates. **The language model does not write Cypher.** Each template is deterministic, uses the extracted entities as parameters, and returns named information.

#### a. Question Types
Support at least **10 question types (intents)**, with at least one in each row of the table below. An intent is a family of questions the assistant can recognise and route to retrieval, not a single sentence: *"wins for a driver at a circuit"* is one intent and covers every driver and every circuit. You choose the intents. The DE questions from Milestone 1 represent intents and can be used.

| Intent | Example question types | Example user question |
| :--- | :--- | :--- |
| **Driver performance** | Season points and wins; career podiums; average finish at a circuit | *"How many podiums did Leclerc get in 2022?"* |
| **Constructor performance** | Season points; reliability over a period | *"How reliable was Williams between 2014 and 2021?"* |
| **Head-to-head** | Teammate comparison in shared races | *"Who finished ahead more often, Norris or Ricciardo at McLaren?"* |
| **Race and circuit facts** | Race winner and podium; races held at a circuit; circuit location | *"Who won the 2019 German Grand Prix?"* |
| **Qualifying and grid** | Pole positions; grid vs. finish gains; Q3 appearances | *"Which driver gained the most places from the grid at Monza in 2021?"* |
| **Pit stops and strategy** | Fastest pit stops in a race; average stops per driver | *"What was the fastest pit stop at the 2023 Qatar Grand Prix?"* |
| **Season and history** | Championship points leader; drivers per season; team changes between seasons | *"Which drivers changed teams between 2020 and 2021?"* |

**Requirements:**
* At least **three** types must cross two or more hops (for example `Result` to `Race` to `Season`, or `Result` to `Race` to `Circuit`).
* At least **two** types must take more than one entity.
* At least **six** of the ten must be new relative to the five Milestone 2 verification queries.
* **Out-of-scope intent:** questions the graph cannot answer receive a message saying that the assistant does not have the knowledge to answer them.
* **Podium-prediction intent:** routes messages such as *"Predict Norris at the 2024 Miami Grand Prix"* to the prediction path in Section 4.
* The table lists 7 intents. Adding the out-of-scope intent and the podium-prediction intent gives 9, so you must define **one more intent** to reach the required 10. Each intent must handle **4 different questions**, not 4 paraphrases of the same question.

#### b. Cypher Templates
Write parameterised Cypher templates that cover all your question types. One question does not mean one query: a single dynamic template can answer many questions depending on the input parameters, and a question type may also need more than one template. Use query parameters and never concatenate user text into Cypher.

Respect the Milestone 2 relationship directions and conventions. Return named columns. End each template with `LIMIT` or with an aggregation, so the context passed to the language model stays small.

Pass the entities extracted in Section 1.b as the parameters and execute the template. If the query returns no rows, say that the knowledge graph has no data for that question. Do not ask the language model to fill the gap from its own knowledge.

---

### 3. LLM Layer

#### a. Grounded Answers
The language model turns the retrieved rows into a sentence. It must use only the retrieved context. Structure the prompt in three parts:

* **Persona:** for example, *"You are a helpful assistant."* It is highly recommended to change the persona to a more meaningful one.
* **Context:** the user's question, the detected intent, the extracted entities, and the results.
* **Task:** answer using only the context; quote numbers exactly; say when the context is insufficient; state the scope of the figures (what the data covers and excludes). Do not add a count or a name that is not in the context.

**Requirements:**
* Answers should be conversational but precise. Support follow-up questions with the entity cache from Section 1.b.
* Compare at least **three models** on the same prompts and the same retrieved context. Mix families and sizes. Paid APIs are not required: free tiers or locally hosted open-weight models are enough (for example through Groq, OpenRouter, Hugging Face, or Ollama). You choose the provider and the models.
* Also compare **zero-shot** and **few-shot** prompting of the grounded-answer prompt: run the same model on the same results with and without worked example answers in the prompt, and report the difference.
* Keep your API key out of the repository (for example in a config file that is not committed, or an environment variable).
* If a call fails, the interface shows only `"API connection error"`. The answer then falls back to a direct reading of the retrieved results, so the user still sees the facts.

#### b. What the Chat Compares
The chat lets the user choose two of your compared models and shows both answers side by side for the same question and the same results. This is the comparison the user sees while using the system. The written evaluation reports all the models you compared.

Log every turn: the user message, the intent, the entities, the template, the Cypher, the retrieved results, the prompt, the answer, the model, the latency, and the token counts.

---

### 4. Podium Prediction Explainer

The assistant must run your saved Milestone 1 podium model on one feature row, either pre-filled from a chat message or entered manually, and explain the prediction without calling it a cause.

#### a. Input
Support two input modes:
1. **Using Chat:** When the user asks the chat about a driver and supplies some pre-race information, the intent classifier routes the message to the podium-prediction intent. The app then switches to the prediction view and fills each input field with the matching entity extracted from the message. Features the user did not supply are filled with default values and shown in gray. The user can edit any value, then press the **Predict** button.
2. **Manual features:** The user enters the pre-race feature values your Milestone 1 model expects. Designing this input is part of your task: for each feature, decide the input type, the valid range (justified from the data), and how the form guides the user (labels, units, help text, limits). A value that is missing or outside the valid range is refused with a clear message, and no probability is returned.

#### b. Prediction
Load your saved Milestone 1 model together with its full preprocessing from file. Do not fit a new model. Return the podium probability and the class (podium or not podium) using the threshold you selected in Milestone 1. Compute the local explanation (SHAP and/or LIME) live for the row being scored, with the same explainer setup you used in Milestone 1.

#### c. Explanation
The explanation prompt receives the feature values, the strongest positive and negative local contributions, the SHAP global importance findings from Milestone 1, and pre-race graph facts retrieved with your Cypher templates (for example the driver's record at the circuit or the constructor's reliability), restricted to races whose date is strictly before the scored race.

The explanation must:
* Say which features pushed the probability up, which pushed it down, and by roughly how much.
* Be readable by a non-technical Formula 1 fan.
* Not present a feature contribution as a cause of a podium. A high contribution means the model relies on that feature.
* Not invent a feature, a value, or a fact that is not in the context.

---

### 5. User Interface

Build a **Streamlit** application with two views.

**The chat view lets a user:**
1. Ask a question and see the conversation history, including clarifying questions, in the same thread.
2. Choose two language models and compare their answers to the same question. Each answer is labelled with the model ID. If the key is missing or the call fails, both columns still show the wording taken from the retrieved results, and a failed call is reported only as `"API connection error"`.
3. View the retrieved context for an in-domain answer. The retrieval trace shows:
   * the detected intent and the extracted entities;
   * if the retrieved results are graphical (nodes and edges), you must display the subgraph showing the nodes and edges: a drawing, a node table, an edge table, and the relationship statements (for example `(Result)-[:BY_DRIVER]->(Driver)`), not only as JSON. If they are not graphical (for example a maximum or an average), just return the value;
   * the Cypher query and its parameters;
   * the raw results.
4. Receive an out-of-domain refusal with no retrieval trace. Questions the graph cannot answer and questions outside Formula 1 are in this group.
5. See the entity cache, so a follow-up such as *"And in 2020?"* is visibly using the previous driver or team.

**The prediction view lets a user:**
1. Arrive from the chat with the fields pre-filled, or enter the pre-race features through the input you designed in Section 4.
2. See the podium probability, the predicted class, and the actual finish when that race is known.
3. See a local explanation plot (SHAP or LIME) beside the language-model explanation.

*Note:* There is no screenshot upload, no photo input, no voice input or output, and no generated-chart path.

---

### 6. Experiments, Results, and Improvements

Your final report must include:

* **System architecture:** a diagram that explains the pipeline: preprocessing, then retrieval, then the language model, then the interface, and the separate prediction path. Questions and predictions share one knowledge graph.
* **Question types and examples:** the table of intents, the entities each one needs, one example phrasing, and the result of the matching template.
* **Intent comparison:** accuracy and a confusion matrix for the rule-based and the neural approach, and which one is deployed.
* **LLM comparison:** at least three models, the same prompts, and the same retrieved context. Metrics are:
  * answer correctness (numbers and names from the original values),
  * faithfulness (no extra counts or names),
  * out-of-scope refusal,
  * explanation fidelity (the features named in the explanation match the top local contributions),
  * mean latency, and
  * mean input and output tokens.
* **Qualitative sheet:** a 1–5 fluency rubric for two raters, and a flag for causal language, covering the answers of every compared model to the 4 questions per intent (40 in total). The script prints the items. The scores are filled in by hand.
* **Error analysis:** group failures by stage (intent, entity, query, the model misread the rows, hallucination) and show examples.
* **A before-and-after note:**
  * Zero-shot vs. few-shot: report both prompting styles on the same models and rows.
  * Then pick the weakest metric on your first run (for example faithfulness), apply an improvement such as a prompt change, few-shot examples, or better entity extraction, rerun, and record both numbers.
* **Improvements:** describe the enhancements you made to overcome the limitations you found. Include at least one example of an issue or limitation you faced during your work and the step you took to fix it.
* **Remaining limitations:** what the system cannot do well and what would need further work.

**Test sets:**
* At least **30 question-answering items** across the types, including ambiguous names, follow-ups, out-of-scope questions, and empty results. The gold facts are the results returned by the correct template at evaluation time, not hand-written numbers.
* At least **5 driver-and-race explanation cases**, including one predicted podium and one predicted non-podium.

> There is no performance threshold. You are evaluated on integration, design, functionality, and the attempts you made to improve the system.

---

## Task Allocation

Each team member owns one part of the system. During the evaluation, each member is assessed mainly on the part they own, and every member is expected to explain how a question flows through the whole pipeline.

| Member | Part | Responsibilities |
| :---: | :--- | :--- |
| **1** | Intent classification and entity extraction | Section 1.a and the extraction part of 1.b: both intent classifiers, the labelled intent set, its confusion matrix and accuracy, and entity extraction, including missing or ambiguous entities. |
| **2** | Graph retrieval | Section 2: the question types, the Cypher templates, and empty-result handling. Section 4: the podium prediction and its explanation. Also the question-answering test set and the error analysis. |
| **3** | LLM layer | Section 3: the grounded-answer prompt, the model comparison, zero-shot vs. few-shot, the evaluation metrics, and the before-and-after improvement. |
| **4** | Session state and integration | Connecting the stages into one working system: the session cache from 1.b and follow-up handling, clarification turns, the log and retrieval trace, and the Streamlit application (Section 5), including validation of the manual feature input. |

---

## Submission Guidelines

Submit the GitHub repository on a branch named **`Milestone3`** through the following link: [https://forms.gle/A43ddkNJEt3CJ8p67](https://forms.gle/A43ddkNJEt3CJ8p67).

The repository contains:
* the preprocessing,
* the templates,
* the language-model layer,
* the prediction module,
* the interface,
* the evaluation scripts,
* the test sets, and
* a `README` that explains how to run the application and the report. The `README` states how the pre-race features are computed, that the graph schema is unchanged, and which kinds of questions are refused.

The repository must remain **private**. Change it to **public** during the first 5 minutes of your evaluation in front of the TA.