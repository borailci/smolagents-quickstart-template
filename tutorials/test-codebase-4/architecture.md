# System Architecture

## Overview

The system is designed for high availability.

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
```

## Scaling

We use Kubernetes for scaling.
