# Notes App — Specification

Read this file for general architectural tasks or double-check the exact database structure and tech stack.
Keep your replies extremely concise and focus on conveying the key information. 
Avoid unnecessary messages and long code snippets.


## Overview

A simple Notes system with full CRUD functionality.

## Features

- Create a note
- View all notes
- Update a note
- Delete a note

## Data Model

Each note stores:

| Field | Type | Required |
|-------|------|----------|
| Heading (title) | string | Yes |
| Text content | string | Yes |
| Creation timestamp | datetime | Yes |
| Last updated timestamp | datetime | No — only set when edited |
