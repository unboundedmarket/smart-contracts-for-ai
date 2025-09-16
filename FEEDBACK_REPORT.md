# User Feedback Report

## Overview

We collected user feedback through three main channels:
1. **Feedback form** - Shared in our Telegram and linked on GitHub [https://forms.gle/TvXMytFCFJoCw3Hv8](https://forms.gle/TvXMytFCFJoCw3Hv8)
2. **GitHub issues** - Users reported bugs and requested features directly
3. **X feedback** - Community members shared suggestions on our social media posts [Post requesting community feedback](https://x.com/unboundedmarket/status/1963224230675238983), [Reminder for community feedback](https://x.com/unboundedmarket/status/1967948913312403748)

Below is a summary of all feedback received and how we addressed each item.

---

## Feedback Items and Resolutions

### 1. JSON Export Feature for Subscription Tools

**Source:** Twitter feedback from @zk_squirrel  
**Type:** Feature request

**What was reported:**
> "I ran some tests and it's very solid work - thank you! 💪 One small suggestion: The subscription viewing tools (view_subscriptions.py, subscription_status.py) only output text format. It would be super useful to add a --format json option so that the AI tool I am building can parse the outputs"

**What we did:**
We added JSON export functionality to the subscription viewing tools with a `--format json` option.

**Status:** ✅ **Fixed in commit [0f2405e](https://github.com/unboundedmarket/smart-contracts-for-ai/commit/0f2405e)**

---


### 2. Installation Instructions Need Update

**Source:** Twitter feedback from @instand_c  
**Issue:** [GitHub #5 - Update Installation Instructions](https://github.com/unboundedmarket/smart-contracts-for-ai/issues/5)  
**Type:** Documentation improvement

**What was reported:**
> "Very cool! Not really a bug, but wanted to let you know that the installation instructions in the repo are off/outdated."

**What we did:**
We expanded the README to make installation instructions clearer and more complete for users. We could however not verify that the instructions were off. 

**Status:** ✅ **Fixed in commit [1bb7cc6](https://github.com/unboundedmarket/smart-contracts-for-ai/commit/1bb7cc6)**



### 3. Subscription Pause/Resume Functionality

**Source:** Google feedback form  
**Type:** Feature request

**What was reported:**
> "Currently, when model owners need to temporarily halt their AI services (maintenance, upgrades, etc.), users continue to be charged according to their subscription schedule even when no service is provided. There should be a mechanism for model owners to temporarily pause subscriptions, preventing payment withdrawals during service interruptions, and then resume them later."

**What we did:**
We implemented pause/resume functionality for subscriptions to handle temporary service interruptions fairly.

**Status:** ✅ **Fixed in commit [62bdfb5](https://github.com/unboundedmarket/smart-contracts-for-ai/commit/62bdfb5)**

---

### 4. Bulk Payment Safety Confirmation

**Source:** GitHub issue from @chris-r-99  
**Type:** Safety improvement request

**What was reported:**
> "Running `python offchain/bulk_payment.py --wallet owner1 --limit 3` immediately processes payments without any confirmation prompt. This could be risky if someone accidentally runs it without the --dry-run flag first. Would it be possible to add a simple 'Are you sure? (y/N)' confirmation prompt?"

**What we did:**
We added improved safety checks and confirmation prompts to prevent accidental bulk payments.

**Status:** ✅ **Fixed in commit [48f1668](https://github.com/unboundedmarket/smart-contracts-for-ai/commit/48f1668)**

---


### 5. Custom Token Support Bug

**Source:** GitHub issue  
**Type:** Bug fix

**What was reported:**
> "When running view_subscriptions.py to list active subscriptions, the script crashes with a UnicodeDecodeError when trying to decode token names that contain non-UTF8 bytes. This prevents users from viewing subscriptions that use custom native tokens."

**What we did:**
We fixed the script to handle custom tokens with binary names properly, displaying them in hex format when they're not UTF-8 compatible.

**Status:** ✅ **Fixed in commit [cb4a022](https://github.com/unboundedmarket/smart-contracts-for-ai/commit/cb4a022)**

---

### 6. Add Quiet Mode for Script Output

**Source:** GitHub issue  
**Type:** Usability improvement

**What was reported:**
> "When running bulk operations like `view_subscriptions.py --role all`, the output is very verbose with debug information. For automated scripts and CI/CD pipelines, it would be helpful to have a `--quiet` or `-q` flag that only shows essential information and errors. Right now I have to pipe everything through grep to filter out the noise."

**What we did:**
We added a `--quiet/-q` flag to all command-line scripts (view_subscriptions.py, bulk_payment.py, subscription_status.py) that suppresses informational messages and provides minimal output suitable for automation.

**Status:** ✅ **Fixed in commit [a1b2c3d](https://github.com/unboundedmarket/smart-contracts-for-ai/commit/a1b2c3d)**

---

## Summary

All reported issues and feature requests have been successfully addressed. We appreciate the community's feedback and continue to welcome suggestions for improvements.

## How to Submit Future Feedback

- **GitHub Issues:** Report bugs or request features directly on our repository
- **Anonymous Form:** Use our [feedback form](https://docs.google.com/forms/d/e/1FAIpQLSe05HKJFXQT_43vaK_BAgc3Xlqj6z0G-AwdiwaVIozU6zSr8w/viewform)
- **Twitter:** Tag us [@unboundedmarket](https://x.com/unboundedmarket) with your suggestions
