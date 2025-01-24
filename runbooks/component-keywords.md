# Key words for ACM component test failure

## Component Name - Global Hub

It contains the following failure types, and the corresponding key words are listed below.

### Product Bug 

  1. Expect <bool>: false to be true
  2. no data/condition
  3. invalid value
  4. failed to
  5. not ready/health/active/same/scheduled
  6. due to
  7. time out...not found, this falure is probably 80% product bug.

### Automation Bug

  1. Test Panicked
  2. Expect <bool>: false to be true

### System Issue

  1. no rows in result set. suggest to run job again.

## Component Name - Server Foundation

It contains the following failure types, and the corresponding key words are listed below.

### Product bug

  1. failed to
  2. no condition 
  3. not find
  4. Expected <bool>: false to be true
  5. no cluster
  6. not ready
  
### Automation bug 

  2. Expected <bool>: false to be true  
  3. Test Panicked 

### System issue:
  1. time out

## Component Name - grc

### Product bug

  1. AssertionError: Expected

### Automation bug

  1. Expected to find element
  2. Expected to include
  3. Timed out retrying
  4. Expected to find content
  5. expected '0' to include '1'
  6. command exited with a non-zero code

### System issue

  1. Timed out retrying
  2. `cy.click()` failed
  3. before all. that means dependent package not be installed

## Component Name - alc

### Product bug

### Automation bug
  1. Expected to find element
  2. Expected to find content 
  3. command exited with a non-zero code
  4. subscription is not ready
  5. to include

### System issue
  1. Timed out retrying
  2. before all. that means dependent package not be installed

## Component Name - Obs

### Product bug
  1. should have 3 but got 2 ready replicas

