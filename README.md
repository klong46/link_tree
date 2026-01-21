# Link Tree
Link Tree is a light-weight Flask application that builds a tree structure modelling the relationships between successive page links. 

The model can be used to map the relationship of different URLs, determine the most efficient route between URLs, and implement performance testing on user paths.

# Quick Start

Initialize and activate Python virtual environment:

`python -m env venv`

`source env/bin/activate`

Install dependencies:

`pip install -r requirements.txt`

Run local server:

`flask run`

# Usage

### Get Links Containing Keyword

`GET /find_keyword/{keyword}?click_limit={click_limit}`

Retrieves all links containing given keyword. Response contains matching links and degrees of separation.

#### Parameters

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `keyword` | string | Yes | Keyword to search for. |
| `click_limit` | int | No | Degrees of separation to search before cancelling request. |

