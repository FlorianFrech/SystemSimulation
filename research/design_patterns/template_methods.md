Gamma, E. (Ed.). (1995). Design patterns: Elements of reusable object-oriented software. Addison-Wesley.

# Design Patterns: Template Methods

## Intent

- Define the skeleton of an algorithm in an operation
- Some steps are deferred to sub-classes
- Template methods lets sub-classes redefine certain steps
- This does not change the structure of the algorithm

## Motivation

- The template method defines an algorithm in terms of abstract operations that sub classes override to provide concrete behavior
- Template method fixes the ordering of the ordering of the abstract operations
- Each subclass overrides the abstract methods to its own needs

## Applicability

- Implement the invariant parts of an algorithm once
- The behavior that can vary is left up to sub-classes that have to implement the related parts
- Common behavior among sub classes should be factored and localized in a common class to avoid code duplication
- Identify the differences in the existing code, then separate the differences into new operations and replace differing code with a template method that calls one of these new operations
- Template methods call “hook” operations at specific points, permitting extensions only at those points

## Participants

- Abstract Class
    
    - Defines the abstract primitive operations that concrete sub classes define to implement steps of an algorithm
    - implements a template method defining the skeleton of an algorithm
    - template method calls primitive operations as well as operations defined in Abstract class or those of other objects
- Concrete Class
    
    - Implements the primitive operations to carry out subclass-specific steps of the algorithm
    - Relies on the abstract class to implement the invariant steps of the algorithm

## Consequences

- Factoring out common behavior in library classes
- Lead to an inverted control: Don’t call us, we’ll call you
- Parent class calls the operations of a subclass and not the other way around
- Template methods call the following kind of operations:
    
    - Concrete operation on ConcreteClass
    - concrete Abstract Class operations (operations that are generally useful to sub-classes)
    - primitive operations (abstract operations)
    - factory methods
    - hook operations: provide default behavior that sub-classes can extend if necessary. A hook operation often does nothing by default.
- Important to specify which operations are hooks (may be overridden) and which are abstract (must be overridden)
- Subclass writers need to understand which operations are designed for overriding
- Subclass can extend a parent class operation’s behavior by overriding the operation and calling the parent operation explicitly
- Idea: call a hook operation from a template method in the parent class, subclass can then  override this hook operation (hook operation does nothing in parent class, but subclass overrides the HookOperation to extend its behavior)