"""
This module implements a natural language parser for car search queries.
"""
from typing import Dict, List, Optional, Tuple, Union
import re
from dataclasses import dataclass
from enum import Enum
import logging

class TokenType(Enum):
    """Types of tokens that can be parsed from the query."""
    FIND = "find"
    CAR = "car"
    PRICE = "price"
    LOCATION = "location"
    YEAR = "year"
    CONDITION = "condition"
    OPERATOR = "operator"
    NUMBER = "number"
    AND = "and"
    OR = "or"
    BETWEEN = "between"
    HIGHER = "higher"
    LOWER = "lower"
    THAN = "than"
    UNKNOWN = "unknown"

@dataclass
class Token:
    """Represents a token in the query."""
    type: TokenType
    value: str
    position: int

@dataclass
class SearchCondition:
    """Represents a search condition in the query."""
    field: str
    operator: str
    value: Union[str, int, float]
    logical_operator: str = "&&"

class QueryParser:
    def __init__(self):
        self.tokens: List[Token] = []
        self.conditions: List[SearchCondition] = []
        
    def tokenize(self, query: str) -> List[Token]:
        """Convert the query string into tokens."""
        query = query.lower().strip()
        tokens = []
        position = 0
        
        # Define patterns for different token types
        patterns = [
            (TokenType.FIND, r"^find\b"),
            (TokenType.CAR, r"\b(toyota|honda|nissan|mazda|suzuki|mitsubishi|lexus|bmw|mercedes|audi|volkswagen|hyundai|kia|ford|chevrolet|dodge|jeep|chrysler|volvo|land rover|range rover|porsche|ferrari|lamborghini|bentley|rolls royce|jaguar|maserati|aston martin|mclaren|bugatti|pagani|koenigsegg|rimac|lucid|tesla|rivian|polestar|genesis|infiniti|acura|subaru|mini|fiat|alfa romeo|peugeot|renault|citroen|skoda|seat|opel|vauxhall|saab|rover|mg|tata|mahindra|maruti|hyundai|kia|honda|toyota|nissan|mazda|suzuki|mitsubishi|lexus|bmw|mercedes|audi|volkswagen|ford|chevrolet|dodge|jeep|chrysler|volvo|land rover|range rover|porsche|ferrari|lamborghini|bentley|rolls royce|jaguar|maserati|aston martin|mclaren|bugatti|pagani|koenigsegg|rimac|lucid|tesla|rivian|polestar|genesis|infiniti|acura|subaru|mini|fiat|alfa romeo|peugeot|renault|citroen|skoda|seat|opel|vauxhall|saab|rover|mg|tata|mahindra|maruti)\b"),
            (TokenType.PRICE, r"\b(price|cost|value|worth)\b"),
            (TokenType.LOCATION, r"\b(in|at|near|around|close to)\b"),
            (TokenType.YEAR, r"\b(year|model|make)\b"),
            (TokenType.CONDITION, r"\b(new|used|old|second hand|pre owned|pre-owned)\b"),
            (TokenType.OPERATOR, r"\b(>=|<=|>|<|=|!=)\b"),
            (TokenType.NUMBER, r"\d+(?:,\d+)*(?:\.\d+)?"),
            (TokenType.AND, r"\band\b"),
            (TokenType.OR, r"\bor\b"),
            (TokenType.BETWEEN, r"\bbetween\b"),
            (TokenType.HIGHER, r"\b(higher|more than|above)\b"),
            (TokenType.LOWER, r"\b(lower|less than|below)\b"),
            (TokenType.THAN, r"\bthan\b"),
        ]
        
        while position < len(query):
            matched = False
            for token_type, pattern in patterns:
                match = re.match(pattern, query[position:])
                if match:
                    value = match.group(0)
                    tokens.append(Token(token_type, value, position))
                    position += len(value)
                    matched = True
                    break
            
            if not matched:
                # Skip whitespace
                if query[position].isspace():
                    position += 1
                else:
                    # Unknown token
                    tokens.append(Token(TokenType.UNKNOWN, query[position], position))
                    position += 1
        
        return tokens

    def parse_price_condition(self, tokens: List[Token], start_idx: int) -> Tuple[Optional[SearchCondition], int]:
        """Parse price-related conditions."""
        if start_idx >= len(tokens):
            return None, start_idx
            
        current_idx = start_idx
        condition = None
        
        # Handle "higher/lower than" format
        if current_idx + 2 < len(tokens):
            if tokens[current_idx].type in [TokenType.HIGHER, TokenType.LOWER]:
                if tokens[current_idx + 1].type == TokenType.THAN:
                    if tokens[current_idx + 2].type == TokenType.NUMBER:
                        value = float(tokens[current_idx + 2].value.replace(",", ""))
                        operator = ">=" if tokens[current_idx].type == TokenType.HIGHER else "<="
                        condition = SearchCondition("pricing", operator, value)
                        current_idx += 3
                        return condition, current_idx
        
        # Handle "between X and Y" format
        if current_idx + 3 < len(tokens):
            if tokens[current_idx].type == TokenType.BETWEEN:
                if tokens[current_idx + 1].type == TokenType.NUMBER:
                    if tokens[current_idx + 2].type == TokenType.AND:
                        if tokens[current_idx + 3].type == TokenType.NUMBER:
                            min_price = float(tokens[current_idx + 1].value.replace(",", ""))
                            max_price = float(tokens[current_idx + 3].value.replace(",", ""))
                            condition = SearchCondition("pricing", ">=", min_price)
                            self.conditions.append(condition)
                            condition = SearchCondition("pricing", "<=", max_price)
                            current_idx += 4
                            return condition, current_idx
        
        return None, start_idx

    def parse_car_condition(self, tokens: List[Token], start_idx: int) -> Tuple[Optional[SearchCondition], int]:
        """Parse car-related conditions."""
        if start_idx >= len(tokens):
            return None, start_idx
            
        current_idx = start_idx
        car_terms = []
        
        while current_idx < len(tokens):
            if tokens[current_idx].type == TokenType.CAR:
                car_terms.append(tokens[current_idx].value)
                current_idx += 1
            else:
                break
        
        if car_terms:
            # Create a condition that matches any of the car terms
            condition = SearchCondition("title", "~", "|".join(car_terms))
            return condition, current_idx
            
        return None, start_idx

    def parse(self, query: str) -> List[SearchCondition]:
        """Parse the query and return a list of search conditions."""
        self.tokens = self.tokenize(query)
        self.conditions = []
        current_idx = 0
        
        while current_idx < len(self.tokens):
            token = self.tokens[current_idx]
            
            # Skip "find" keyword
            if token.type == TokenType.FIND:
                current_idx += 1
                continue
            
            # Parse price conditions
            price_condition, new_idx = self.parse_price_condition(self.tokens, current_idx)
            if price_condition:
                self.conditions.append(price_condition)
                current_idx = new_idx
                continue
            
            # Parse car conditions
            car_condition, new_idx = self.parse_car_condition(self.tokens, current_idx)
            if car_condition:
                self.conditions.append(car_condition)
                current_idx = new_idx
                continue
            
            current_idx += 1
        
        return self.conditions

    def build_pocketbase_query(self, conditions: List[SearchCondition]) -> str:
        """Build a PocketBase query string from the conditions."""
        if not conditions:
            return ""
            
        query_parts = []
        for condition in conditions:
            if condition.field == "title":
                # For title search, use regex matching
                query_parts.append(f'title ~ "{condition.value}"')
            else:
                # For other fields, use direct comparison
                query_parts.append(f'{condition.field} {condition.operator} {condition.value}')
        
        return " && ".join(query_parts)

def parse_search_query(query: str) -> str:
    """
    Parse a natural language query and return a PocketBase query string.
    
    Args:
        query (str): Natural language search query
        
    Returns:
        str: PocketBase query string
    """
    parser = QueryParser()
    conditions = parser.parse(query)
    return parser.build_pocketbase_query(conditions) 