# Requirement: Database Integration with CSV 

## Status 
Denied 

## Context

The project requires robust storage for structured data (orders and products). CSV files were considered as they are easy to use and require minimal setup. 

## Decision

Integration with CSV files for storing and querying data was denied. 

## Rationale

1. CSV files are not suitable for complex queries or efficient data retrieval. 

2. Difficulty in scaling as the dataset grows. 

## Consequences

Indicating that an alternative approach, i.e. using SQL database for data integration, should be explored. 
