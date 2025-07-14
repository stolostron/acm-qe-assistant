# Key words for ACM component test failure

## Component Name - Global Hub

It contains the following failure types, and the corresponding key words are listed below.

### Product Bug 

  1. the MGH CR was not health
  2. the kafka is not ready
  3. not update in the database
  4. no data for the metric
  5. no condition in status
  6. Unable to connect to database
  7. not same with the db data
  8. did not find
  9. invalid value
  10. failed to get
  11. not ready/health/active/same/scheduled
  12. status is Pending due to
  13. status is Failed due to

### Automation Bug

  1. Test Panicked
  2. Expected.*to be true

### System Issue

  1. no rows in result set

## Component Name - Server Foundation

It contains the following failure types, and the corresponding key words are listed below.

### Product bug

  1. failed to get
  2. failed to find
  3. failed to delete
  4. failed to create the managedcluster resources
  4. did not find the MCE csv
  5. no condition in status
  6. no cluster
  7. not ready
  
### Automation bug 

  1. Expected.*to be true  
  2. Test Panicked 

### System issue:
  1. time out

## Component Name - grc

### Product bug

  1. AssertionError: Expected to

### Automation bug

  1. Expected to find element
  2. Expected to include
  3. Timed out retrying
  4. Expected to find content
  5. Expected not to find content
  6. expected '0' to include '1'
  7. failed because the command exited with a non-zero code
  8. k8srequiredlabelsinvalid does not have the expected message "validation.gatekeeper.sh" denied the request
  9. Internal error occurred: failed calling webhook "ocm.mutating.webhook.admission.open-cluster-management.io"
  10. Timed out retrying
  11. does not have the expected message

### System issue

  2. `cy.click()` failed because this element is `disabled`
  3. before all. that means dependent package not be installed
  4. Login failed (401 Unauthorized)

## Component Name - alc

### Product bug
 1. subscription is not ready within time limit
 2. Route is not ready within time limit

### Automation bug
  1. Expected to find element
  2. Expected to find content 
  3. because the command exited with a non-zero code
  4. to include

### System issue
  1. Timed out retrying
  2. before all. that means dependent package not be installed
  3. not ready within time limit

## Component Name - Obs

### Product bug
  1. should have 3 but got 2 ready replicas
  2. should have 1 but got 0 ready replicas

### Automation bug
  1. not found
  2. Expected.*to be true

### System issue
  1. no such host

## Component Name - clc

### Product bug
### Automation bug
  1. Expected to find content
  2. failed because it targeted a disabled element
  3. Expected to find element
  4. `cy.click()` failed
  5. The following error originated from your test code, not from Cypress
  
### System issue
  1. 503: Service Unavailable
  2. before all
  3. due to cluster pool issue

## Component Name - search

### Product bug
### Automation bug
### System issue 

## Component Name - volsync

### Product bug
### Automation bug
1. Cannot read properties of undefined (reading 'slice')
### System issue 
