# TTESV Alignment Evidence Contract Investigation

**Status:** Hold
**Version:** 0.5.0

No production alignment data may be regenerated from this investigation
until a concrete application-alignment representation satisfying the established
minimum representational capability has been established and verified.

---

# Engineering Problem

The Ultimate Bible App currently represents Strong's token alignment in
`verse_token_tags`.

Investigation of the installed data and the TTESV source demonstrated that
the existing representation cannot be treated as authoritative alignment
evidence.

The installed `verse_token_tags` data contains only ESV alignment. Investigation
also demonstrated that portions of the installed ESV alignment contain both
lexical-identity corruption and token-position drift introduced by the
historical import process.

The historical TTESV importer was structurally incapable of preserving all
relationships represented by TTESV. Among other limitations, it forced numeric
Strong's identifiers into a Greek identity, treated punctuation as independent
translation tokens, and could not preserve multiple lexical relationships with
their original source structure.

The immediate problem is therefore not how to populate missing alignment data.
It is to determine what TTESV evidence licenses the application to assert about
translation-token ↔ lexical-identity relationships without manufacturing
relationships, specificity, certainty, or causal explanation not established
by the evidence.

---

# Governing Forge Findings

This investigation applies existing Forge findings, particularly:

- FD-0032 — Methodological Provenance Preservation
- FD-0033 — Authority Evidence Establishment for Controlled Stage Admission
- FD-0034 — Interpretive Evidentiary Standing for Controlled Stage Admission

Investigation depth is bounded by:

- FI-0006 — Ultimate Legitimacy of Applicable Governance

The FI-0006 boundary applies:

> Interesting Dependency ≠ Blocking Dependency

> Unresolved Question ≠ Required Present Investigation

A deeper question is therefore pursued only when it is demonstrated to block
the bounded engineering operation.

This investigation does not reopen questions of ultimate epistemic,
constitutive, or governance legitimacy merely because evidentiary authority,
interpretation, standing, or provenance appears in the engineering problem.

---

# Governing Engineering Law

The Forge established the following bounded engineering law:

> An application may assert only the relationship and specificity established
> by its evidence; transformation of that evidence cannot create authority for
> information the evidence did not establish.

A related constraint is:

> Interpretation may transform representation; it may not manufacture
> evidentiary meaning.

These principles govern every transformation from TTESV source evidence to an
application-visible token ↔ lexical relationship.

---

# Established Source Findings

The investigation has established the following facts relevant to the alignment
contract.

TTESV preserves relationships richer than the existing `verse_token_tags`
representation.

The TTESV source documentation establishes ordinary RHS encoding conventions
for Hebrew and Greek Strong's identifiers.

TTESV permits multiple RHS lexical relationships for a source mapping. Source
cardinality therefore cannot be collapsed merely because an application
representation expects one `strongs_id`.

TTESV LHS numeric expressions do not have one universal semantic role.

The same `lhs_raw` syntax can represent different semantic roles, including
within the same verse. Ezra 8:18 provides a decisive witness in which the same
raw numeric form participates in different roles.

Among 343,666 mappings independently supported as ESV positions by the
installed ESV witness, TTESV source order is perfectly consistent with ESV
positional order. Zero source-order failures were observed in that population.

A separate population of 2,206 mappings is positionally unsupported against
the installed ESV witness and forms a structured terminally observed
verse-boundary population.

Global splitting of internal ASCII hyphens was tested as a possible repair and
was falsified as a general solution. Although it made 656 previously
unsupported mappings position-compatible, it changed the established token
occurrence for 5,037 control mappings.

Existing supported anchors therefore constrain proposed repairs.

A candidate token projection cannot earn support from repairing one mapping
when the transformation required contradicts independently supported mappings
in the same verse.

Genesis 5:28 establishes a separate class of disagreement. In that verse,
surrounding positional anchors remain stable while TTESV preserves the numeric
expression `182` at the textual location where the retained ESV artifact
contains `122`.

Visual inspection of the retained `ESV.pdf` confirmed that the retained PDF
itself contains `122` in Genesis 5:28. The disagreement was therefore not
introduced by PDF text extraction, CSV conversion, or database import at this
witness.

The retained PDF artifact consequently cannot be granted standing as an
authoritative witness for the ESV text assumed by TTESV merely because the
artifact is named `ESV.pdf`.

Genesis 5:28 establishes textual disagreement with positional stability. It
does not explain the separate 2,206-mapping terminal positional-divergence
population.

For ordinary TTESV mappings, available evidence may establish positional
divergence without establishing whether its cause is textual insertion or
deletion, tokenization-boundary difference, source-witness difference, or
another cause.

---

# Source Evidence and Derived Assertion

The investigation established that the following must remain distinct:

```text
SOURCE ASSERTION
      ≠
INTERPRETATION
      ≠
PROJECTION RESULT
      ≠
CAUSAL EXPLANATION
```

A source assertion preserves what the source actually supplies.

An interpretation assigns semantic meaning to the source assertion where such
meaning is not already directly established by the source convention.

A projection evaluates an interpreted assertion against a particular target
witness under a particular projection rule.

A projection result records what that bounded comparison established.

A causal explanation asserts why the projection produced that result and
therefore requires independent evidentiary standing.

Failure at a later layer does not rewrite an earlier layer.

In particular:

> Failure to project evidence onto a target representation does not invalidate
> the evidence being projected.

---

# Directly Verifiable Relationships

A relationship may be directly represented when its semantics are established
by a bounded source convention and its application requires no material
interpretive choice.

For ordinary documented TTESV RHS forms, a transformation such as:

```text
TTESV raw RHS
    08141
      |
      | established source convention
      v
    H8141
```

may be represented as a bounded normalization.

The normalized identifier does not replace the raw source expression.

Likewise, where the source establishes multiple RHS relationships, that
multiplicity is itself source evidence and must remain recoverable.

For example, a source relationship equivalent to:

```text
A → B1 + B2 + B3
```

cannot be losslessly replaced by three unrelated rows if doing so destroys the
fact that the source asserted one relationship with cardinality three.

Preservation of constituent values alone is therefore insufficient.

The evidentiary structure relating those values must also remain recoverable.

---

# Material Interpretation

Where semantic meaning depends upon contextual discrimination, interpretation
is a distinct derived assertion.

Therefore:

```text
lhs_raw ≠ lhs_interpretation
```

A raw TTESV expression must not be silently replaced by the semantic
interpretation assigned to it.

Where an interpretation requires a material bridge between source evidence and
the bounded proposition relied upon by the application, the standing of that
interpretive bridge must be independently established.

This follows the distinction preserved by FD-0034:

```text
Interpretation ≠ Interpretive Evidentiary Standing
```

Correct-looking output, expertise, consensus, convenience, or deterministic
implementation does not by itself establish the standing of the
interpretation.

---

# Unresolved Interpretation

Where available evidence cannot discriminate among live interpretations, the
correct result is:

```text
INTERPRETATION_UNRESOLVED
```

An unresolved interpretation is not permission to select the statistically
common, operationally convenient, or application-compatible interpretation.

It is itself an evidentiary result.

Therefore:

> Uncertainty established by evidence is information and must not be erased by
> transformation.

The source assertion must remain preserved even when its semantic
interpretation remains unresolved.

---

# Projection

Projection is a further derived relationship.

Conceptually:

```text
SOURCE ASSERTION
        +
INTERPRETATION
        +
TARGET WITNESS
        +
PROJECTION RULE
        =
PROJECTION RESULT
```

A projection result is meaningful only relative to the source assertion,
interpretation, target witness, and projection under which it was derived.

Projection results may include states equivalent to:

```text
SUPPORTED

DIVERGENT

UNRESOLVED
```

A derived assertion therefore inherits the conditions under which it was
derived.

Changing the target witness may legitimately change the projection result.

Changing the projection rule may legitimately change the projection result.

Those results are not contradictions when their derivational conditions are
different.

Target-witness identity and projection-rule identity must therefore remain
recoverable wherever downstream standing depends upon the projection result.

The Anvil further established:

> **Projection success does not constitute evidentiary support unless the
> criterion establishing support has itself acquired sufficient standing. A
> comparison result inherits the standing of the relationships required to
> produce it.**

---

# Projection Result Is Not Causal Explanation

A projection may establish a bounded result such as:

```text
SOURCE POSITION 23
        |
        | projection P
        v
TARGET WITNESS W

POSITION_UNAVAILABLE
```

That result establishes only that the source assertion could not be satisfied
under projection P against target witness W.

It does not independently establish:

```text
TOKENIZATION DIFFERENCE

TEXTUAL INSERTION

TEXTUAL DELETION

BAD TTESV DATA

BAD TARGET DATA
```

or any other causal explanation.

Therefore:

> Projection result ≠ causal explanation.

And:

> Evidence of divergence grants authority to assert divergence, not authority
> to assert its cause.

Where cause is not independently established, the cause remains unresolved.

---

# Genesis 5:28 Witness

Genesis 5:28 provides a decisive witness separating positional divergence from
surface textual disagreement.

TTESV preserves:

```text
$Gen 5:28
02=<03929>
04=<02421>
182=<03967>+<08141>+<08084>+<08147>
05=<08141>
07=<03205>
09=<01121>
```

Against the retained ESV witness, the surrounding positional relationships
remain consistent:

```text
02
04
05
07
09
```

while TTESV independently preserves the numeric expression:

```text
182
```

at the textual location where the retained ESV artifact contains:

```text
122
```

The token stream has therefore not drifted at this witness.

The disagreement concerns surface content occupying an otherwise supported
position.

This establishes the following discriminator:

> When independently supported TTESV positional anchors remain consistent
> across a verse, but independently evidenced surface information contradicts
> the installed token occupying the supported position, the discrepancy cannot
> be attributed solely to positional tokenization.

This witness establishes that textual disagreement exists.

It does not establish the cause of every positional divergence elsewhere in
the corpus.

---

# Textual Conservation and Divergence

TTESV does not generally preserve complete English surface text.

Therefore absence of an English token from TTESV cannot establish absence of
that token from the translation witness.

Positional evidence may establish that two token streams diverge.

It does not, by itself, establish what textual material was conserved, added,
deleted, substituted, or tokenized differently.

Only where TTESV independently preserves relevant surface-content evidence may
textual conservation or disagreement be tested directly.

Therefore:

> A source may establish textual divergence only where it actually preserves
> evidence about textual content; positional evidence cannot be promoted into
> textual evidence merely because textual divergence would explain it.

For much of the positionally divergent population, the available TTESV and
retained ESV evidence may leave the cause underdetermined.

That unresolved state must be preserved.

---

# Authoritative Preservation Boundary

The Forge investigated which surviving elements must be authoritative
persisted evidence, which may be reproducibly derived, and which may exist only
as application cache data.

The initial Forge result was:

> The authoritative boundary is determined not by whether information is
> stored, but by whether the evidentiary information and standing it carries
> can be reconstructed without introducing a new interpretive assumption.

The Anvil identified that mere deterministic reproducibility is insufficient.

A transformation can deterministically reproduce the same result while
containing an interpretation whose standing was never established.

The Anvil therefore refined the result to:

> The authoritative preservation boundary is determined not by whether
> information is materialized, but by whether the evidentiary content,
> structure, and standing required by downstream assertions can be
> reconstructed from independently preserved evidence through transformations
> whose applicable standing is itself established. Where such reconstruction
> would require a new evidentiary or interpretive determination, the necessary
> evidence or established determination must itself be preserved.

This distinction survived Anvil inspection.

---

# Reconstructing Value and Standing

The Anvil established that reproducing a value is not necessarily equivalent
to reproducing the evidentiary authority for that value.

Therefore:

> Reconstructing a value ≠ reconstructing its evidentiary standing.

For example, a persisted interpretation may say:

```text
interpretation = POSITION
```

but if the evidence and established interpretive relationship supporting that
determination have been lost, the system may still possess the value while no
longer possessing the standing necessary to assert it.

Where downstream authority depends upon an established determination that
cannot itself be reproducibly recovered from preserved evidence and
established transformations, the necessary determination or its sufficient
evidentiary basis must be preserved.

---

# Authority and Materialization

The Anvil established:

> Persistence does not confer evidentiary authority.

A value does not become authoritative merely because it occupies a database
row.

The converse also holds:

> Authoritative evidence does not necessarily require database
> materialization.

An independently preserved source artifact may remain grounding evidence even
when its parsed representation is regenerated as needed.

The Anvil further established:

> Authority is relative to the proposition for which evidence is offered; it
> is not an intrinsic property conferred by storage.

An artifact may therefore occupy different evidentiary roles for different
bounded propositions.

For example, the retained `ESV.pdf` may be evidence of what that particular
artifact contains without thereby establishing that its text is the
authoritative ESV witness assumed by TTESV.

Finally:

> Authority must not propagate merely because provenance does.

A derived assertion may possess sufficient standing for a bounded application
operation without becoming source evidence.

---

# Derivation and Materialization

The investigation distinguishes representational necessity from persistence
necessity:

> Representational necessity ≠ persistence necessity.

Information that must remain distinguishable does not necessarily require its
own permanently materialized database representation.

A derived assertion may remain reproducible rather than authoritative
materialized evidence when the following remain sufficiently preserved:

```text
SOURCE EVIDENCE
        +
RELEVANT CONTEXT
        +
ESTABLISHED TRANSFORMATION
        =
REPRODUCIBLE DERIVED ASSERTION
```

Therefore:

> Derivability does not require materialization.

However, reproducibility must preserve more than constituent values.

Where relevant, it must preserve or recover:

```text
relationship
cardinality
specificity
uncertainty
source identity
target identity
transformation identity
applicable standing
```

A representation is not losslessly reconstructive merely because all
individual values can still be found somewhere in the system.

---

# Source Artifact Identity

A filename alone is insufficient to establish stable artifact identity.

If an artifact changes while retaining the same filename, a derived assertion
that records only that filename may silently change its evidentiary referent.

An immutable content fingerprint may therefore be used to establish which
particular artifact participated in a derivation.

The fingerprint establishes artifact identity and integrity for this bounded
purpose.

It does not establish semantic or normative authority.

Therefore:

```text
ARTIFACT FINGERPRINT
        =
ARTIFACT IDENTITY / INTEGRITY SUPPORT

ARTIFACT FINGERPRINT
        ≠
EVIDENTIARY AUTHORITY
```

---

# Historical and Current Derivations

A transformation may later be corrected, replaced, or superseded.

If a historical derived assertion matters as evidence of what the application
previously asserted, its historical derivation conditions must remain
recoverable.

If the derived material was only a disposable cache with no historical
evidentiary role, it may instead be regenerated under the currently
established derivation contract.

Therefore:

```text
CURRENT REPRODUCIBILITY
        ≠
HISTORICAL REPRODUCIBILITY
```

This distinction does not require every historical cache to be retained.

It requires that historical derivation conditions be preserved where a
historical derived assertion itself carries downstream evidentiary standing.

---

# Persistence Classification

The surviving conceptual hierarchy is:

```text
PRESERVED EVIDENTIARY FOUNDATION
        |
        v
REPRODUCIBLE / ESTABLISHED DERIVATIONS
        |
        v
SUPPORTED APPLICATION RELATIONSHIPS
        |
        v
DISPOSABLE APPLICATION CACHE
```

At minimum, source evidence whose loss would destroy non-reconstructable
evidentiary information must be preserved together with sufficient artifact
identity.

Lossless parsed source representations may be reproducibly derived where the
source artifact and applicable parsing transformation remain sufficient to
recover them.

Semantic interpretations may be reproducibly derived where their evidence,
context, transformation, and applicable standing remain recoverable.

Projection results may be reproducibly derived where the source assertion,
interpretation, target witness, projection rule, and applicable standing remain
recoverable.

A non-reproducible established evidentiary determination must itself be
preserved, or its sufficient evidentiary basis must remain preserved, where
downstream standing depends upon that determination.

---

# Role of `verse_token_tags`

The existing `verse_token_tags` table is not authoritative TTESV alignment
evidence.

Its current representation is structurally incapable of independently
preserving all information required by the evidence contract.

Among other things, it cannot independently preserve:

- raw TTESV source assertions;
- source relationship structure;
- source cardinality and multiplicity;
- interpretation distinct from source evidence;
- interpretive standing;
- unresolved interpretation;
- target-witness identity;
- projection-rule identity;
- divergent or unresolved projection results;
- causal uncertainty.

This does not mean `verse_token_tags` is useless.

It may remain suitable as a derived application cache containing
application-ready token ↔ lexical relationships whose sufficient standing has
already been established upstream.

Conceptually:

```text
SOURCE EVIDENCE
        |
        v
INTERPRETATION
        |
        v
PROJECTION
        |
        v
SUPPORTED RELATIONSHIP
        |
        v
verse_token_tags
        |
        v
APPLICATION UI
```

Only affirmative relationships that have reached the required supported state
should be materialized as affirmative token tags.

States such as:

```text
INTERPRETATION_UNRESOLVED

DIVERGENT

PROJECTION_UNRESOLVED
```

are legitimate evidentiary or derivational results, but they are not
affirmative token ↔ lexical relationships.

A cache may omit evidentiary detail only where that detail survives
independently upstream.

Therefore:

> A cache may discard evidentiary detail only when that detail survives
> independently upstream.

Deleting and rebuilding `verse_token_tags` must not require creation of a new
interpretive or evidentiary assumption.

The Anvil further established:

> **A disposable application cache may omit upstream provenance that remains
> independently recoverable, but it may not silently discard part of the
> affirmative relationship it purports to materialize.**

The Genesis 1:4 cardinality witness establishes that one supported target token
occurrence can participate in one relationship with multiple lexical
participants. The present scalar physical `verse_token_tags` schema therefore
cannot faithfully materialize every complete supported application
relationship.

This finding does not authorize modification of the schema. The stronger
question of whether the atomic token-to-lexical association model is itself
insufficient remains unresolved and is the next bounded investigation.

---

# Anvil-Surviving Representation Requirements

The investigation currently requires the system to be capable of representing
or recoverably establishing the following conceptual lifecycle:

```text
SOURCE ARTIFACT
    identity + immutable fingerprint
        |
        v
SOURCE ASSERTION
    raw source expressions
    source location
    source order
    source cardinality
        |
        v
INTERPRETATION
    interpreted meaning
    interpretation status
    interpretation rule identity
    applicable standing
        |
        v
PROJECTION
    target witness identity
    projection rule identity
        |
        v
PROJECTION RESULT
    SUPPORTED
    DIVERGENT
    UNRESOLVED
    target relationship if established
        |
        v
OPTIONAL DERIVED CACHE
    verse_token_tags
```

Separately:

```text
PROJECTION RESULT
        ≠
CAUSAL EXPLANATION
```

This is a conceptual representation requirement.

It does not establish that each conceptual layer requires a separate database
table or permanently materialized record.

No SQL schema is authorized by this finding.

---

# Engineering HOLD

Until a concrete application-alignment representation satisfying the
established minimum capability has been established and verified, the
following remain unauthorized:

- regeneration of production `verse_token_tags`;
- rewriting production `data/bible.db`;
- manufacturing KJV alignment;
- copying ESV alignment to KJV;
- forcing all TTESV LHS expressions into positional semantics;
- inferring Hebrew identity merely because a mapping occurs in the Old
  Testament;
- inferring Greek identity merely because a mapping occurs in the New
  Testament;
- collapsing source-supported lexical multiplicity into one lexical identity;
- inventing specificity not supplied by the evidence;
- adopting global ASCII-hyphen splitting as a repair;
- treating the current STEP ESV 2025 text as the historical TTESV witness;
- assuming Genesis 5:28 represents a particular ESV edition revision without
  evidence establishing that relationship;
- treating the retained ESV artifact as an unquestioned authoritative
  measuring stick;
- converting positional divergence into a causal explanation without
  independent evidence;
- altering `data/strongs.db` or lexical-resolver semantics to hide alignment
  deficiencies;
- patching the UI merely to conceal missing or unresolved alignment.

Read-only investigation and bounded derived experiments remain permitted.

The source evidence itself must not be rewritten in order to make it conform
to an application representation.

---

# FI-0006 Boundary

FI-0006 remains Deferred.

Questions concerning ultimate evidence, digital identity, universal
epistemology, ultimate governance legitimacy, or similar deeper foundations do
not re-enter merely because this investigation concerns evidence,
interpretation, provenance, or standing.

The controlling boundary remains:

> Interesting Dependency ≠ Blocking Dependency.

> Unresolved Question ≠ Required Present Investigation.

FI-0006 or another deeper investigation may re-enter only if the bounded
engineering operation cannot establish sufficient authority without resolving
that dependency.

No such blocker has presently been demonstrated.

---

# Current Anvil Result

The distinction among authoritative evidence, established derivations,
supported application relationships, and disposable application caches
survived Anvil inspection.

Genesis 1:4 establishes that one supported target occurrence can participate
in one relationship with multiple lexical participants. The present scalar
physical `verse_token_tags` schema is therefore insufficient as a universal
materialization.

Genesis 1:2 establishes that multiple target occurrences can jointly
participate in one lexical relationship where independent token-level
decomposition would increase relational specificity. The independent
token-to-lexical association model is therefore insufficient as a universal
representation of complete supported TTESV relationships.

The Anvil further refined the minimum application-alignment capability by
requiring reconstruction through transformations whose applicable standing is
established. Deterministic reproducibility alone remains insufficient.

The following statements survive:

> Source assertion != interpretation != projection result != causal
> explanation.

> Reconstructing a value != reconstructing its evidentiary standing.

> Persistence does not confer evidentiary authority.

> Derivability does not require materialization.

> Representational necessity != persistence necessity.

> Authority is relative to the proposition for which evidence is offered; it
> is not an intrinsic property conferred by storage.

> Authority must not propagate merely because provenance does.

> A cache may discard evidentiary detail only when that detail survives
> independently upstream.

> Projection success does not constitute evidentiary support unless the
> criterion establishing support has itself acquired sufficient standing. A
> comparison result inherits the standing of the relationships required to
> produce it.

> A disposable application cache may omit upstream provenance that remains
> independently recoverable, but it may not silently discard part of the
> affirmative relationship it purports to materialize.

> Complete participant preservation != complete relationship preservation.

> Increasing field cardinality does not repair missing relationship topology.

> Physical decomposition != semantic decomposition.

> Row multiplicity != evidentiary independence.

> A representation may physically decompose a relationship only when the
> complete supported relationship remains recoverable without making a new
> evidentiary or interpretive determination.

The minimum-capability result is Anvil-surviving.

The evidence establishes required relational semantics but does not establish a
replacement physical schema.

Production alignment regeneration therefore remains on Hold.

---

# Genesis 1:4 Cardinality Witness

The next bounded experiment tested the smallest discriminator capable of
resolving the physical scalar-schema question:

> Does at least one sufficiently established supported application relationship
> contain one target occurrence and multiple lexical participants?

The TTESV source documentation establishes that two-digit LHS numbers identify
ESV 2011 word positions and that `+` indicates more than one English word is
tagged or more than one Hebrew/Greek word is tagged to it.

The producer documentation itself supplies Genesis 1:4 as an explanatory
example. It states that the ESV word `separated` is tagged by both `<00914>` and
`<00996>` because there is no separate English word representing `<00996>`.

The TTESV source assertion for Genesis 1:4 preserves:

```text
11=<00914>+<00996>
```

Under the established ordinary RHS convention, the lexical participants
normalize without an additional material interpretive choice to:

```text
<00914> -> H914
<00996> -> H996
```

The retained application ESV witness contains Genesis 1:4 as:

```text
And God saw that the light was good. And God separated the light from the
 darkness.
```

Under the bounded whitespace projection used for this witness, the target
occurrences are:

```text
 9: And
10: God
11: separated
12: the
13: light
14: from
15: the
16: darkness.
```

The source mapping, producer explanation, and target projection therefore
converge on one target occurrence participating in one alignment relationship
with two lexical participants:

```text
Genesis 1:4 / position 11 / separated
                    |
                    v
          ALIGNMENT RELATIONSHIP
             /             \
          H914             H996
```

This witness establishes the cardinality proposition required by the bounded
physical-schema test:

> **A complete supported application relationship can contain one target token
> occurrence and multiple lexical participants.**

The present `verse_token_tags` primary key identifies one target token
occurrence, while the row provides one scalar `strongs_id`. The present
physical schema therefore cannot faithfully materialize this Genesis 1:4
relationship as a complete affirmative relationship without omitting an
established lexical participant or changing the semantics of the existing
scalar representation.

The bounded result is:

> **The present scalar physical `verse_token_tags` schema is insufficient to
> faithfully materialize every complete supported application relationship.**

This result does not establish that an atomic token-to-lexical association model
is itself insufficient. A representation capable of preserving multiple
lexical associations for one target occurrence could potentially represent this
1:N witness without relational loss.

Therefore:

> **Physical scalar-schema insufficiency != atomic relationship-model
> insufficiency.**

The installed historical `verse_token_tags` rows for Genesis 1:4 are not used
to establish this relationship. Those rows exhibit the previously established
historical importer defects, including punctuation-induced token drift and
forced Greek lexical identity. The cardinality result stands on the TTESV
source assertion, its producer documentation, the established RHS convention,
and the bounded target projection.

This finding does not authorize modification of the schema or regeneration of
production alignment data.

---

# Genesis 1:2 Relational Topology Witness

The Genesis 1:4 witness established scalar physical-schema insufficiency. It
did not establish whether independent token-to-lexical associations are
universally sufficient as the underlying relationship model.

The next bounded experiment therefore tested relational topology.

The initial discriminator asked for a supported multi-target/multi-lexical
relationship whose topology could not be faithfully decomposed into independent
token-to-lexical associations.

Inspection of the TTESV producer documentation exposed that this formulation
was unnecessarily restrictive. Non-decomposable topology does not require
multiplicity on both sides of the relationship.

The producer documentation states that sometimes two adjacent English words
must be tagged together and supplies Genesis 1:2 as the explanatory example.
It states that `<08414>` is tagged by `without form` because either English
word individually would be misleading.

The exact TTESV source assertion is:

```text
04+05=<08414>
```

Under the established ordinary RHS convention:

```text
<08414> -> H8414
```

The retained application ESV witness contains the relevant target sequence:

```text
 1: The
 2: earth
 3: was
 4: without
 5: form
 6: and
 7: void,
```

The source assertion, producer explanation, and bounded target projection
therefore converge on:

```text
Genesis 1:2

target participants
    position 4: without
    position 5: form
          \       /
           \     /
            \   /
             \ /
      ALIGNMENT RELATIONSHIP
               |
               v
             H8414
```

The decisive feature is not merely that two target participants exist. The
producer explicitly explains that either English word individually would be
misleading.

The evidence therefore establishes the joint relationship:

```text
{without, form} <-> H8414
```

It does not license replacement of that relationship with independently
affirmative assertions equivalent to:

```text
without <-> H8414
form    <-> H8414
```

Such decomposition would convert co-participation in one established
relationship into independently affirmative token-to-lexical relationships.

Therefore:

> **Complete participant preservation != complete relationship preservation.**

And:

> **If decomposition converts a jointly established relationship into
> independently affirmative relationships, decomposition increases relational
> specificity.**

Genesis 1:2 establishes that a relationship may be non-decomposable even when
multiplicity occurs on only one side.

The bounded result is:

> **An independent token-to-lexical association model is insufficient as a
> universal representation of complete supported TTESV application
> relationships.**

This does not prohibit separate physical records for relationship participants.
Separate records may be used where their semantics preserve, or recoverably
reference, the common relationship and do not convert relationship membership
into independent correspondence.

Therefore:

> **Physical decomposition != semantic decomposition.**

> **Row multiplicity != evidentiary independence.**

The current `verse_token_tags` representation has no mechanism, under its
present token-level association semantics, to preserve that positions 4 and 5
jointly participate in one relationship to H8414.

Genesis 1:2 therefore establishes a topology deficiency distinct from the
Genesis 1:4 scalar-cardinality deficiency.

This finding does not authorize a replacement schema or production alignment
regeneration.

---

# Minimum Application-Alignment Capability

The Genesis 1:4 and Genesis 1:2 witnesses establish independent constraints on
any application-alignment representation.

Genesis 1:4 requires independently variable lexical-side cardinality:

```text
R1
target participants  = {separated}
lexical participants = {H914, H996}
```

Genesis 1:2 requires recoverable target-side grouping:

```text
R2
target participants  = {without, form}
lexical participants = {H8414}
```

Preserving all constituent values is not sufficient when their established
relational structure is lost.

The Forge established the following minimum capability, and the Anvil passed it
with refinement:

> **The minimum application-alignment capability is the ability to preserve, or
> reconstruct through transformations whose applicable standing is established,
> each complete supported relationship as the finest affirmative relational
> unit established by the evidentiary chain, with independently variable target
> and lexical participant cardinality, recoverable relationship grouping, and
> every internal correspondence actually established by that chain, while
> adding no participant, correspondence, independence, specificity, grouping,
> or certainty not established by the evidence.**

Target participants must remain identifiable as occurrences within an
identified projection of an identified target witness.

Lexical participants must remain at the specificity established by the
alignment evidence rather than specificity introduced by subsequent lexical
resolution.

The following constraints survive Forge and Anvil inspection:

> **A valid representation must preserve relational structure, not merely all
> constituent values.**

> **Increasing field cardinality does not repair missing relationship
> topology.**

> **A relationship may be non-decomposable even when multiplicity exists on
> only one side.**

> **Finest affirmative relational unit != smallest number of participants.**

> **Established relational semantics != required physical schema.**

> **A representation may physically decompose a relationship only when the
> complete supported relationship remains recoverable without making a new
> evidentiary or interpretive determination.**

A richer scalar field alone is therefore insufficient. Allowing multiple
Strong's identifiers per target occurrence could represent the Genesis 1:4
lexical cardinality but would not preserve the joint target relationship
established by Genesis 1:2.

The evidence establishes the semantic capability required of the eventual
representation. It does not establish whether that capability should be
implemented through database relationship records, membership records,
structured derived files, references to an upstream relationship model, or
another physical design.

The existing `verse_token_tags` concept may still have value as a disposable
application cache. Its failure as a universal self-sufficient representation
does not establish that it must be deleted.

---

# Next Bounded Question

The scalar-cardinality and independent-association questions are now resolved.

Genesis 1:4 establishes that the present scalar physical `verse_token_tags`
schema cannot faithfully materialize every complete supported relationship.

Genesis 1:2 establishes that independent token-to-lexical associations cannot
universally preserve every complete supported relationship.

The next bounded engineering question is:

> **What concrete derived representation can satisfy the established minimum
> application-alignment capability while remaining reconstructable through
> transformations whose applicable standing is established and suitable for
> the application's runtime requirements?**

This is an architecture question constrained by the evidence contract.

It does not authorize production regeneration, database migration, or selection
of a replacement physical schema before the candidate representation has been
established and verified.

No deeper dependency is to be pursued unless it is demonstrated to block this
bounded engineering decision.

---

# Status

| Field | Value |
|---|---|
| Status | Hold |
| Version | 0.5.0 |


The TTESV Alignment Evidence Contract Investigation memorializes the
project-specific evidentiary findings governing translation-token and
lexical-identity alignment in the Ultimate Bible App.

The evidence contract and minimum alignment representation have survived Forge
and Anvil inspection.

Genesis 1:4 establishes that the present scalar physical `verse_token_tags`
schema cannot faithfully materialize every complete supported application
relationship.

Genesis 1:2 establishes that independent token-to-lexical associations are not
a universally sufficient relationship model because an established
relationship may require multiple target occurrences to participate jointly.

The minimum application-alignment capability has now survived Anvil inspection.
The eventual representation must preserve or reconstruct, through
transformations whose applicable standing is established, the cardinality,
grouping, and relational topology of each complete supported relationship.

The investigation remains on Hold because a concrete derived representation
satisfying that capability has not yet been established and verified.

Production alignment regeneration remains on Hold.

FD-0032, FD-0033, and FD-0034 remain the governing Forge findings applied by
this investigation.

FI-0006 remains Deferred and has not satisfied its re-entry condition through
this investigation.

The next bounded question concerns concrete representation architecture, not
whether the present scalar or independent-association models are universally
sufficient.

---

# Version History

| Version | Status | Description |
|---|---|---|
| 0.1.0 | Hold | Initial memorialization of the TTESV alignment evidence |
| | | contract investigation. |
| 0.2.0 | Hold | Incorporated Anvil-surviving source, interpretation, |
| | | projection, |
| | | preservation-boundary, reproducibility, and application-cache findings. |
| 0.3.0 | Hold | Added Anvil refinements concerning projection |
| | | standing and complete application-cache relationship |
| | | cardinality. |
| 0.4.0 | Hold | Established the Genesis 1:4 supported 1:N cardinality |
| | | witness and physical scalar-schema insufficiency; separated |
| | | that result from the unresolved atomic topology question. |
| 0.5.0 | Hold | Established the Genesis 1:2 N:1 topology witness and |
| | | independent-association model insufficiency; established the |
| | | Anvil-surviving minimum application-alignment capability. |


---
