
# Dashboard Frontend Analysis

## 1. Overview

The `agent-lightning-dashboard` package provides the frontend for the agent-lightning dashboard. It is a single-page application built with React, Redux, and Mantine. It displays information about resources and rollouts.

## 2. File-by-File Analysis

### `dashboard/src/main.tsx`

- **Purpose**: This is the main entry point of the application. It renders the root `App` component and provides the Redux store to the entire application using the `Provider` component from `react-redux`.

### `dashboard/src/App.tsx`

- **Purpose**: This is the root component of the application. It sets up the Mantine UI library, including the theme, CSS variables, and color scheme. It then renders the `Router` component, which is responsible for handling the application's routing.

### `dashboard/src/pages/Resources.page.tsx`

- **Purpose**: This page displays a paginated and sortable table of resources.
- **Key Components**:
    - `ResourcesPage`: The main component for the page. It fetches resource data using the `useGetResourcesQuery` hook from RTK Query. It manages the state of the table (search term, sorting, pagination) using Redux.
    - `ResourcesTable`: A component that renders the actual table of resources. It receives data and callbacks from the `ResourcesPage` component.
    - `ResourcesTree`: A component that is rendered as a row expansion in the `ResourcesTable`. It displays the resources in a tree-like structure.
- **Data Flow**:
    1. The `ResourcesPage` component fetches data from the `/api/resources` endpoint using `useGetResourcesQuery`.
    2. The user can interact with the table by searching, sorting, and changing pages.
    3. These interactions dispatch actions to the Redux store to update the state.
    4. The changes in the Redux store trigger a re-fetch of the data with the new query parameters.
- **Integration Points**:
    - Redux store: for state management.
    - RTK Query: for data fetching.
    - `ResourcesTable` and `ResourcesTree` components.

### `dashboard/src/pages/Rollouts.page.tsx`

- **Purpose**: This page displays a paginated, sortable, and filterable table of rollouts.
- **Key Components**:
    - `RolloutsPage`: The main component for the page. It fetches rollout data using the `useGetRolloutsQuery` hook from RTK Query. It manages the state of the table (search term, filters, sorting, pagination) using Redux.
    - `RolloutTable`: A component that renders the actual table of rollouts. It receives data and callbacks from the `RolloutsPage` component.
    - `RolloutAttemptsContent`: A component that is rendered as a row expansion in the `RolloutTable`. It fetches and displays the attempts for a given rollout.
- **Data Flow**:
    1. The `RolloutsPage` component fetches data from the `/api/rollouts` endpoint using `useGetRolloutsQuery`.
    2. The user can interact with the table by searching, filtering, sorting, and changing pages.
    3. These interactions dispatch actions to the Redux store to update the state.
    4. The changes in the Redux store trigger a re-fetch of the data with the new query parameters.
- **Integration Points**:
    - Redux store: for state management.
    - RTK Query: for data fetching.
    - `RolloutTable` and `RolloutAttemptsTable` components.
    - `Drawer` component: for displaying raw JSON and traces.

## 3. Public Interface

The main entry point of the application is the `App` component in `dashboard/src/App.tsx`. The pages are rendered by the `Router` component, which is not shown in the provided files.

The `ResourcesPage` and `RolloutsPage` components are the main pages of the application. They are not designed to be used as standalone components and are expected to be rendered within the application's routing structure.

## 4. API Reference

### `ResourcesPage` Component

| Prop                 | Type                                    | Description                                      |
| -------------------- | --------------------------------------- | ------------------------------------------------ |
| `(none)`             | `N/A`                                   | This component does not accept any props.        |

### `RolloutsPage` Component

| Prop                 | Type                                    | Description                                      |
| -------------------- | --------------------------------------- | ------------------------------------------------ |
| `(none)`             | `N/A`                                   | This component does not accept any props.        |

## 5. Use Cases

- **Viewing Resources**: Users can view a list of all resources, search for specific resources, and sort the list.
- **Viewing Rollouts**: Users can view a list of all rollouts, search for specific rollouts, filter by status and mode, and sort the list.
- **Viewing Rollout Details**: Users can expand a rollout to view its attempts.
- **Viewing Raw Data**: Users can view the raw JSON data for a rollout.
