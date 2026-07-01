# Database Transactions and ACID

A transaction groups several database operations so they succeed or fail as a unit.
The classic example is a bank transfer: debiting one account and crediting another must
either both happen or neither, or money is created or destroyed. The guarantees that
make this safe are summarized by the acronym ACID.

Atomicity means the transaction is all-or-nothing. If any statement fails, the whole
transaction is rolled back and the database looks as though it never ran. There is no
state in which the debit happened but the credit did not.

Consistency means a transaction moves the database from one valid state to another,
never leaving constraints violated. Isolation means concurrent transactions do not see
each other's uncommitted changes. Finally, durability guarantees that once a
transaction commits, its effects survive even a crash or power loss, because they have
been written to persistent storage.

Isolation is the property with the most nuance, because perfect isolation is expensive.
Databases offer several isolation levels that trade strictness for concurrency. A weak
level permits a dirty read, where one transaction sees another's uncommitted data;
stronger levels forbid it but allow fewer transactions to run at once.

The strongest level is serializable isolation, under which the outcome is guaranteed to
equal some sequential order of the transactions, as if they had run one at a time. It
eliminates every anomaly but reduces throughput the most, so systems often choose a
weaker level deliberately when the application can tolerate the relaxed guarantees.
