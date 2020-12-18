# RecipeRadar Ingredient Parser

The RecipeRadar Ingredient Parser takes a set of free-text ingredient descriptions, and extracts product, quantity and unit information from them.

For example, given the ingredient text: `50ml of water`, the `ingredient-parser` service can indicate that the `product=water`, `units=ml` and `quantity=50`.

This functionality is provided to the [crawler](https://www.github.com/openculinary/crawler) service so that it can extract additional data from each recipe crawled.

## Install dependencies

Make sure to follow the RecipeRadar [infrastructure](https://www.github.com/openculinary/infrastructure) setup to ensure all cluster dependencies are available in your environment.

## Development

To install development tools and run linting and tests locally, execute the following commands:

```sh
$ make lint tests
```

## Local Deployment

To deploy the service to the local infrastructure environment, execute the following commands:

```sh
$ make
$ make deploy
```
