#!/usr/bin/env bash

set -e  # exit on error

DIR="papers"

# Create directory if it doesn't exist
mkdir -p "$DIR"

# Move into the directory
cd "$DIR"

# Download papers
wget -O attention_is_all_you_need.pdf https://arxiv.org/pdf/1706.03762
wget -O bert.pdf                       https://arxiv.org/pdf/1810.04805
wget -O vit.pdf                        https://arxiv.org/pdf/2010.11929
wget -O flashattention.pdf             https://arxiv.org/pdf/2205.14135
wget -O gpt3.pdf                       https://arxiv.org/pdf/2005.14165
wget -O scaling_laws.pdf               https://arxiv.org/pdf/2001.08361
wget -O chinchilla.pdf                 https://arxiv.org/pdf/2203.15556
wget -O mixtral.pdf                    https://arxiv.org/pdf/2401.04088
wget -O rag.pdf                        https://arxiv.org/pdf/2005.11401
wget -O dpr.pdf                        https://arxiv.org/pdf/2004.04906
wget -O lora.pdf                       https://arxiv.org/pdf/2106.09685
wget -O prompt_tuning.pdf              https://arxiv.org/pdf/2104.08691
wget -O chain_of_thought.pdf           https://arxiv.org/pdf/2201.11903
wget -O react.pdf                      https://arxiv.org/pdf/2210.03629
wget -O instructgpt.pdf                https://arxiv.org/pdf/2203.02155
wget -O constitutional_ai.pdf          https://arxiv.org/pdf/2212.08073
wget -O clip.pdf                       https://arxiv.org/pdf/2103.00020
wget -O gat.pdf                        https://arxiv.org/pdf/1710.10903
wget -O mmlu.pdf                       https://arxiv.org/pdf/2009.03300

echo "All papers downloaded into $DIR/"
