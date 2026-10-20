# Product ownership and independence

This is the normative contract for product ownership, repository organization,
composition, and consumer independence. Apply it when planning, implementing, or
reviewing changes to structure, dependencies, packaging, CI, and tests. Apply it
within the originating task's agreed scope.

## Ownership

`products/` contains consumer-facing products. Each product owns its source,
consumer-used scripts, configuration, documentation, tests, fixtures, and customer
CI where its documented consumer workflows require it.

`maintainer/` contains upstream packaging, release orchestration, repository
administration, and their tests. A packager used only by maintainers belongs here
even when it produces just one product. Maintainer tooling may import or invoke
product capabilities; products do not depend on maintainer tooling.

Source ownership is separate from release-archive contents. Product-owned tests
and development configuration need not ship in a production artifact. Each
artifact includes the components its documented consumer workflows require and
declares its external prerequisites.

## Directory structure

The current source layout keeps the Python runtime, package metadata, and tests
under `products/deployment-kit/`, with its Astro source at root `site/`.
Mode assets live under `products/deployment-kit/ci/gitlab/{operator,prebuilt}/`,
`containers/assessment/`, and `docs/{operator,prebuilt}/`.

The deployment product owns generation and the site build; Prebuilt consumes its
static output and owns deploy-only instructions and CI. Tests and fixtures follow
the capability they exercise. Upstream packaging and release tooling live under
`maintainer/`; catalog source and assessments remain separate products.

## CI and composition

Upstream CI validates the repository and produces releases. Its GitHub workflow
entry points remain under `.github/workflows/`, with upstream packaging and
release tooling owned by `maintainer/`.

Customer CI ships with its product and operates within the customer's instance.
It may assess customer-owned skills, build a site, or deploy it as appropriate to
that product. It does not depend on upstream maintainer workflows at execution
time. A downloadable catalog or wheel does not require a GitLab pipeline merely
because it is a product.

Products may consume other products' release artifacts. Deployment-kit assembly
may also explicitly select and copy source and assets from other products into
its deliverables. Copied components become part of the assembled customer
instance; their authoritative upstream source remains owned by the originating
product. Candidate assembly may use source before its release is published.

Product execution and customer CI use included components or declared artifact
dependencies, rather than resolving code from sibling product source directories
or maintainer tooling. For example, an installed assessment-kit wheel or an
explicitly assembled copy can provide assessment functionality in an Operator
instance.

## Tests and independence

Product tests own or include their required fixtures and test support. They do
not resolve dependencies by importing sibling product source or test directories.
Tests of a product's behavior with its included or installed dependencies remain
owned by that product. Integration tests of upstream multi-product assembly and
release packaging belong to `maintainer/` and exercise supported product
interfaces and assembled components.

Shared repository development environments are permitted; separate environments
and mechanisms that block imports are not required. Their convenience does not
establish consumer independence.

Demonstrate independence by exercising each artifact's documented consumer
workflows outside the upstream checkout, using its included components and
declared prerequisites. Upstream assembly may run within the checkout. A
prebuilt consumer is checked through installation and deployment; an Operator
instance also exercises its customer-side build and CI as documented.

## Placement examples

| Capability | Owner |
| --- | --- |
| Upstream-only Operator ZIP assembler and its tests | `maintainer/` |
| Generator shipped to customers and also invoked by upstream CI | Deployment product’s Operator mode |
| GitLab job building a customer's Operator instance | Deployment product's `operator/` mode |
| Source skills copied into a deployment-kit deliverable | Originating catalog product; explicitly included during assembly |
| Assessment validation tests and their fixtures | Assessment product |
| Upstream integration test assembling multiple product artifacts | `maintainer/` |
