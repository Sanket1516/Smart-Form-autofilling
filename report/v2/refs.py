# -*- coding: utf-8 -*-
"""References in IEEE style, numbered in the order of first citation in the text.

Only peer-reviewed conference papers are listed. Every entry was checked on 23 October 2026 against its official
publication record: Crossref metadata for the DOI, the ACL Anthology, PMLR, the NeurIPS and ICLR proceedings
sites and the USENIX conference pages. A page range that the official record does not give is left out rather
than guessed. Software products (MongoDB, ChromaDB, FastAPI, LangGraph, React, Playwright, ...) are not cited;
they are named in the text and listed with their versions in Appendix C. More than six authors are shortened
to "et al." as IEEE allows.
"""

NEURIPS = "https://proceedings.neurips.cc/paper_files/paper"
ICLR = "https://proceedings.iclr.cc/paper_files/paper"

REFS = {
    # Retrieval, embeddings and RAG
    "sbert": "N. Reimers and I. Gurevych, “Sentence-BERT: Sentence embeddings using Siamese BERT-networks,” in *Proc. 2019 Conf. Empirical Methods in Natural Language Processing and 9th Int. Joint Conf. Natural Language Processing (EMNLP-IJCNLP)*, Hong Kong, China, Nov. 2019, pp. 3982–3992, doi: 10.18653/v1/D19-1410.",
    "dpr": "V. Karpukhin *et al.*, “Dense passage retrieval for open-domain question answering,” in *Proc. 2020 Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Online, Nov. 2020, pp. 6769–6781, doi: 10.18653/v1/2020.emnlp-main.550.",
    "rag": f"P. Lewis *et al.*, “Retrieval-augmented generation for knowledge-intensive NLP tasks,” in *Advances in Neural Information Processing Systems 33 (NeurIPS 2020)*, Online, Dec. 2020, pp. 9459–9474. [Online]. Available: {NEURIPS}/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html",
    "selfrag": f"A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, “Self-RAG: Learning to retrieve, generate, and critique through self-reflection,” in *Proc. 12th Int. Conf. Learning Representations (ICLR)*, Vienna, Austria, May 2024, pp. 9112–9141. [Online]. Available: {ICLR}/2024/hash/25f7be9694d7b32d5cc670927b8091e1-Abstract-Conference.html",
    "dbnet": "M. Liao, Z. Wan, C. Yao, K. Chen, and X. Bai, “Real-time scene text detection with differentiable binarization,” in *Proc. AAAI Conf. Artificial Intelligence*, vol. 34, no. 7, New York, NY, USA, Feb. 2020, pp. 11474–11481, doi: 10.1609/aaai.v34i07.6812.",
    "injection": "K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and M. Fritz, “Not what you’ve signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection,” in *Proc. 16th ACM Workshop on Artificial Intelligence and Security (AISec ’23)*, co-located with ACM CCS, Copenhagen, Denmark, Nov. 2023, pp. 79–90, doi: 10.1145/3605764.3623985.",
    "pibench": "Y. Liu, Y. Jia, R. Geng, J. Jia, and N. Z. Gong, “Formalizing and benchmarking prompt injection attacks and defenses,” in *Proc. 33rd USENIX Security Symp. (USENIX Security 24)*, Philadelphia, PA, USA, Aug. 2024, pp. 1831–1847. [Online]. Available: https://www.usenix.org/conference/usenixsecurity24/presentation/liu-yupei",
    # Web agents
    "webarena": f"S. Zhou *et al.*, “WebArena: A realistic web environment for building autonomous agents,” in *Proc. 12th Int. Conf. Learning Representations (ICLR)*, Vienna, Austria, May 2024, pp. 15585–15606. [Online]. Available: {ICLR}/2024/hash/4410c0711e9154a7a2d26f9b3816d1ef-Abstract-Conference.html",
    "mind2web": "X. Deng *et al.*, “Mind2Web: Towards a generalist agent for the web,” in *Advances in Neural Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track*, New Orleans, LA, USA, Dec. 2023, pp. 28091–28114, doi: 10.52202/075280-1220.",
    "seeact": "B. Zheng, B. Gou, J. Kil, H. Sun, and Y. Su, “GPT-4V(ision) is a generalist web agent, if grounded,” in *Proc. 41st Int. Conf. Machine Learning (ICML)*, ser. PMLR, vol. 235, Vienna, Austria, Jul. 2024, pp. 61349–61385. [Online]. Available: https://proceedings.mlr.press/v235/zheng24e.html",
    "webvoyager": "H. He *et al.*, “WebVoyager: Building an end-to-end web agent with large multimodal models,” in *Proc. 62nd Annu. Meeting Assoc. Computational Linguistics (ACL), Vol. 1: Long Papers*, Bangkok, Thailand, Aug. 2024, pp. 6864–6890, doi: 10.18653/v1/2024.acl-long.371.",
    "cogagent": "W. Hong *et al.*, “CogAgent: A visual language model for GUI agents,” in *Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition (CVPR)*, Seattle, WA, USA, Jun. 2024, pp. 14281–14290, doi: 10.1109/CVPR52733.2024.01354.",
    "seeclick": "K. Cheng *et al.*, “SeeClick: Harnessing GUI grounding for advanced visual GUI agents,” in *Proc. 62nd Annu. Meeting Assoc. Computational Linguistics (ACL), Vol. 1: Long Papers*, Bangkok, Thailand, Aug. 2024, pp. 9313–9332, doi: 10.18653/v1/2024.acl-long.505.",
    "ferretui": "K. You *et al.*, “Ferret-UI: Grounded mobile UI understanding with multimodal LLMs,” in *Computer Vision – ECCV 2024* (Lecture Notes in Computer Science, vol. 15122). Cham, Switzerland: Springer, 2024, pp. 240–255, doi: 10.1007/978-3-031-73039-9_14.",
    "workarena": "A. Drouin *et al.*, “WorkArena: How capable are web agents at solving common knowledge work tasks?” in *Proc. 41st Int. Conf. Machine Learning (ICML)*, ser. PMLR, vol. 235, Vienna, Austria, Jul. 2024, pp. 11642–11662. [Online]. Available: https://proceedings.mlr.press/v235/drouin24a.html",
    "lcow": f"D. Lee *et al.*, “Learning to contextualize web pages for enhanced decision making by LLM agents,” in *Proc. 13th Int. Conf. Learning Representations (ICLR)*, Singapore, Apr. 2025, pp. 81039–81072. [Online]. Available: {ICLR}/2025/hash/c995a913bc20ca39ce2231b8973be90a-Abstract-Conference.html",
    "webagent": f"I. Gur *et al.*, “A real-world WebAgent with planning, long context understanding, and program synthesis,” in *Proc. 12th Int. Conf. Learning Representations (ICLR)*, Vienna, Austria, May 2024, pp. 52690–52717. [Online]. Available: {ICLR}/2024/hash/e91bf7dfba0477554994c6d64833e9d8-Abstract-Conference.html",
    # Agents, memory and knowledge graphs
    "guisurvey": "D. Nguyen *et al.*, “GUI agents: A survey,” in *Findings of the Assoc. Computational Linguistics: ACL 2025*, Vienna, Austria, Jul. 2025, pp. 22522–22538, doi: 10.18653/v1/2025.findings-acl.1158.",
    "genagents": "J. S. Park, J. O’Brien, C. J. Cai, M. R. Morris, P. Liang, and M. S. Bernstein, “Generative agents: Interactive simulacra of human behavior,” in *Proc. 36th Annu. ACM Symp. User Interface Software and Technology (UIST ’23)*, San Francisco, CA, USA, Oct. 2023, pp. 1–22, doi: 10.1145/3586183.3606763.",
    "tog": f"J. Sun *et al.*, “Think-on-Graph: Deep and responsible reasoning of large language model on knowledge graph,” in *Proc. 12th Int. Conf. Learning Representations (ICLR)*, Vienna, Austria, May 2024, pp. 3868–3898. [Online]. Available: {ICLR}/2024/hash/10a6bdcabbd5a3d36b760daa295f63c1-Abstract-Conference.html",
    "hipporag": "B. Jiménez Gutiérrez, Y. Shu, Y. Gu, M. Yasunaga, and Y. Su, “HippoRAG: Neurobiologically inspired long-term memory for large language models,” in *Advances in Neural Information Processing Systems 37 (NeurIPS 2024)*, Vancouver, BC, Canada, Dec. 2024, pp. 59532–59569, doi: 10.52202/079017-1902.",
    # Form understanding, form filling and form security
    "layoutlm": "Y. Xu, M. Li, L. Cui, S. Huang, F. Wei, and M. Zhou, “LayoutLM: Pre-training of text and layout for document image understanding,” in *Proc. 26th ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining (KDD ’20)*, Virtual Event, CA, USA, Aug. 2020, pp. 1192–1200, doi: 10.1145/3394486.3403172.",
    "ctxform": "M. Hartmann and M. Mühlhäuser, “Context-aware form filling for web applications,” in *Proc. IEEE Int. Conf. Semantic Computing (ICSC)*, Berkeley, CA, USA, Sep. 2009, pp. 221–228, doi: 10.1109/ICSC.2009.83.",
    "crossapp": "S. Wang, Y. Zou, B. Upadhyaya, and J. Ng, “An intelligent framework for auto-filling web forms from different web applications,” in *Proc. IEEE 9th World Congress on Services (SERVICES)*, Santa Clara, CA, USA, Jun. 2013, pp. 175–179, doi: 10.1109/SERVICES.2013.19.",
    "formlm": "Y. Shao *et al.*, “FormLM: Recommending creation ideas for online forms by modelling semantic and structural information,” in *Proc. 2022 Conf. Empirical Methods in Natural Language Processing (EMNLP)*, Abu Dhabi, UAE, Dec. 2022, pp. 8133–8149, doi: 10.18653/v1/2022.emnlp-main.557.",
    "formnexus": "P. Alian, N. Nashid, M. Shahbandeh, and A. Mesbah, “Semantic constraint inference for web form test generation,” in *Proc. 33rd ACM SIGSOFT Int. Symp. Software Testing and Analysis (ISSTA)*, Vienna, Austria, Sep. 2024, pp. 932–944, doi: 10.1145/3650212.3680332.",
    "autofill": "X. Lin, P. Ilia, and J. Polakis, “Fill in the blanks: Empirical analysis of the privacy threats of browser form autofill,” in *Proc. ACM SIGSAC Conf. Computer and Communications Security (CCS)*, Virtual Event, USA, Nov. 2020, pp. 507–519, doi: 10.1145/3372297.3417271.",
    # Supporting techniques
    "minilm": f"W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, “MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers,” in *Advances in Neural Information Processing Systems 33 (NeurIPS 2020)*, Online, Dec. 2020, pp. 5776–5788. [Online]. Available: {NEURIPS}/2020/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html",
    "bcrypt": "N. Provos and D. Mazières, “A future-adaptable password scheme,” in *Proc. 1999 USENIX Annu. Technical Conf., FREENIX Track*, Monterey, CA, USA, Jun. 1999. [Online]. Available: https://www.usenix.org/legacy/events/usenix99/provos.html",
}

ORDER = []  # keys in order of first citation


def c(*keys):
    """Return an in-text citation such as [3] or [3], [4], assigning numbers on first use."""
    nums = []
    for k in keys:
        if k not in REFS:
            raise KeyError(f"unknown reference {k}")
        if k not in ORDER:
            ORDER.append(k)
        nums.append(ORDER.index(k) + 1)
    nums = sorted(set(nums))
    return ", ".join(f"[{n}]" for n in nums)


def uncited():
    return sorted(set(REFS) - set(ORDER))
