from __future__ import annotations

from pathlib import Path

DEFAULT_CONFIG_CONTENTS: dict[str, str] = {
    "configs/deklar-aggregation.json": """{
    "config_type": "deklar_aggregation",
    "config_version": 1,
    "description": "VATTool v1 deklar aggregation rules. Expressions are declarative and allow only sum and subtract.",
    "document_count_rules": {
        "sales_document_count": {
            "source_table": "prodagbi",
            "distinct_key_fields": [
                "document_type",
                "document_number",
                "document_date",
                "counterparty_vat"
            ],
            "note": "Provisional rule. Awaiting accountant confirmation."
        },
        "purchases_document_count": {
            "source_table": "pokupki",
            "distinct_key_fields": [
                "document_type",
                "document_number",
                "document_date",
                "counterparty_vat"
            ],
            "note": "Provisional rule. Awaiting accountant confirmation."
        }
    },
    "field_rules": [
        {
            "target_field": "sales_total_tax_base",
            "expression": {
                "op": "sum",
                "sources": [
                    {
                        "table": "prodagbi",
                        "field": "total_tax_base"
                    }
                ]
            },
            "note": "Fill 01-01 from prodagbi totals (placeholder source field name; adjust to match prodagbi schema)."
        },
        {
            "target_field": "sales_total_vat",
            "expression": {
                "op": "sum",
                "sources": [
                    {
                        "table": "prodagbi",
                        "field": "total_vat"
                    }
                ]
            },
            "note": "Fill 01-20 from prodagbi totals (placeholder source field name; adjust to match prodagbi schema)."
        },
        {
            "target_field": "total_tax_credit",
            "expression": {
                "op": "sum",
                "sources": [
                    {
                        "table": "pokupki",
                        "field": "vat_full_credit"
                    }
                ]
            },
            "note": "Total tax credit derived from pokupki (placeholder source field name; adjust to match pokupki schema)."
        },
        {
            "target_field": "vat_due",
            "expression": {
                "op": "subtract",
                "left": {
                    "op": "sum",
                    "sources": [
                        {
                            "table": "prodagbi",
                            "field": "total_vat"
                        }
                    ]
                },
                "right": {
                    "op": "sum",
                    "sources": [
                        {
                            "table": "pokupki",
                            "field": "vat_full_credit"
                        }
                    ]
                }
            },
            "note": "VAT due = sales_total_vat - total_tax_credit (must be >= 0; enforcement is runtime)."
        },
        {
            "target_field": "vat_refundable",
            "expression": {
                "op": "subtract",
                "left": {
                    "op": "sum",
                    "sources": [
                        {
                            "table": "prodagbi",
                            "field": "total_vat"
                        }
                    ]
                },
                "right": {
                    "op": "sum",
                    "sources": [
                        {
                            "table": "pokupki",
                            "field": "vat_full_credit"
                        }
                    ]
                }
            },
            "note": "VAT refundable uses same formula; runtime will place negative into refundable and 0 into due (implementation rule)."
        }
    ]
}
""",
    "configs/mappings/docoument-type-mapping.json": """{
    "config_type": "document_type_mapping",
    "config_version": 1,
    "default_behavior": "take_leading_two_digits",
    "map": {
        "01 - Invoice": "01",
        "02 - Credit Note": "02"
    }
}
""",
    "configs/mappings/ledger-columns.json": """{
  "config_type": "ledger_columns",
  "config_version": 1,
  "name": "ledger-columns",
  "description": "Canonical internal ledger field names mapped to exact Odoo v19 CSV column names.",
  "company_name": "company_id",
  "company_vat": "company_id/vat",
  "partner_name": "partner_id",
  "counterparty_vat": "partner_id/vat",
  "tax_tag_ids": "tax_tag_ids",
  "balance": "balance",
  "tax_period_source_date": "date",
  "journal_type": "journal_id/type",
  "purchase_doc_number": "ref",
  "sales_move_name": "move_name",
  "document_type": "move_id/l10n_bg_document_type",
  "document_date": "invoice_date",
  "posting_date": "date",
  "sales_doc_number": "move_name"
}
""",
    "configs/mappings/tax-grid-mapping.json": """{
  "config_type": "tax_grid_mapping",
  "config_version": 1,
  "meta": {
    "title": "VATTool tax grid mapping (Odoo v19 → НАП)",
    "notes": [
      "This file maps Odoo tax tags (tax_tag_ids) to target output amount columns.",
      "Logic is strictly tag-based in v1 (no conditional rules).",
      "Each tag may map to multiple targets (multiple columns and/or multiple tables).",
      "Targets may only be 'pokupki' or 'prodagbi' (Deklar is derived separately).",
      "amount_column must match schema internal_name exactly; unknown columns are fatal.",
      "Within one ledger row, two tags must not write to the same (table, amount_column) — fatal collision."
    ],
    "last_updated": "YYYY-MM-DD",
    "maintainer": "PUT_NAME_OR_TEAM",
    "source": "Accountant-provided mapping"
  },
  "defaults": {
    "unknown_tag_behavior": "warn_and_skip_row_if_all_unknown",
    "trim_whitespace": true,
    "sort_tags_canonically": true
  },
  "tags": {
    "11": {
      "label": "",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_20",
          "sign": -1
        }
      ]
    },
    "12_1": {
      "label": "",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_intra_community_acq",
          "sign": 1
        }
      ]
    },
    "12_2": {
      "label": "",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_reverse_charge_82",
          "sign": 1
        }
      ]
    },
    "13": {
      "label": "Example purchase full credit VAT",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_9",
          "sign": -1
        }
      ]
    },
    "14": {
      "label": "Example purchase full credit VAT",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_0_chapter3",
          "sign": -1
        }
      ]
    },
    "15": {
      "label": "Example purchase full credit VAT",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_0_intra_community_supply",
          "sign": -1
        }
      ]
    },
    "16": {
      "label": "Example purchase full credit VAT",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_0_other",
          "sign": -1
        }
      ]
    },
    "17": {
      "label": "",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_services_21_2",
          "sign": -1
        }
      ]
    },
    "18": {
      "label": "",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_69_2_eu",
          "sign": -1
        }
      ]
    },
    "19": {
      "label": "",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "base_exempt",
          "sign": -1
        }
      ]
    },
    "19rc": {
      "label": "UNMAPPED",
      "targets": []
    },
    "21": {
      "label": "",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "vat_20",
          "sign": -1
        }
      ]
    },
    "22": {
      "label": "Example purchase full credit VAT",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "vat_intra_community_and_82",
          "sign": -1
        }
      ]
    },
    "23": {
      "label": "Example purchase full credit VAT",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "vat_for_private_use",
          "sign": -1
        }
      ]
    },
    "24": {
      "label": "Example purchase full credit VAT",
      "targets": [
        {
          "table": "prodagbi",
          "amount_column": "vat_9",
          "sign": -1
        }
      ]
    },
    "30": {
      "label": "Example sales 20% base",
      "targets": [
        {
          "table": "pokupki",
          "amount_column": "base_and_vat_no_credit",
          "sign": 1
        }
      ]
    },
    "31": {
      "label": "",
      "targets": [
        {
          "table": "pokupki",
          "amount_column": "base_full_credit",
          "sign": 1
        }
      ]
    },
    "32": {
      "label": "",
      "targets": [
        {
          "table": "pokupki",
          "amount_column": "base_partial_credit",
          "sign": 1
        }
      ]
    },
    "41": {
      "label": "",
      "targets": [
        {
          "table": "pokupki",
          "amount_column": "vat_full_credit",
          "sign": 1
        }
      ]
    },
    "42": {
      "label": "",
      "targets": [
        {
          "table": "pokupki",
          "amount_column": "vat_partial_credit",
          "sign": 1
        }
      ]
    }
  }
}
""",
    "configs/schemas/deklar-schema.json": """{
    "config_type": "deklar",
    "config_version": 1,
    "schema_name": "deklar_schema",
    "file_encoding": "cp1251",
    "line_length": 590,
    "newline": "CRLF",
    "fields": [
        {
            "id": 1,
            "code": "00-01",
            "internal_name": "vat_number",
            "name_bg": "Идентификационен номер по ДДС на лицето",
            "start_pos": 1,
            "width_guess": 15,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 15,
            "align": "left"
        },
        {
            "id": 2,
            "code": "00-02",
            "internal_name": "taxpayer_name",
            "name_bg": "Наименование на лицето",
            "start_pos": 16,
            "width_guess": 50,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 50,
            "align": "left"
        },
        {
            "id": 3,
            "code": "00-03",
            "internal_name": "tax_period",
            "name_bg": "Данъчен период",
            "start_pos": 66,
            "width_guess": 6,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 6,
            "align": "left",
            "pattern": "YYYYMM"
        },
        {
            "id": 4,
            "code": "00-04",
            "internal_name": "submitter_person",
            "name_bg": "Лице, подаващо данните (ЕГН/име)",
            "start_pos": 72,
            "width_guess": 50,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 50,
            "align": "left"
        },
        {
            "id": 5,
            "code": "00-05",
            "internal_name": "sales_document_count",
            "name_bg": "Брой документи в дневника за продажби",
            "start_pos": 122,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "decimals": 0
        },
        {
            "id": 6,
            "code": "00-06",
            "internal_name": "purchases_document_count",
            "name_bg": "Брой документи в дневника за покупки",
            "start_pos": 137,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "decimals": 0
        },
        {
            "id": 7,
            "code": "01-01",
            "internal_name": "sales_total_tax_base",
            "name_bg": "Общ размер на данъчните основи за облагане с ДДС (Продажби)",
            "start_pos": 152,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2,
            "notes": "Сума от PRODAGBI 02-10, без кодове 11,12,13,04."
        },
        {
            "id": 8,
            "code": "01-20",
            "internal_name": "sales_total_vat",
            "name_bg": "Всичко начислен ДДС (Продажби)",
            "start_pos": 167,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2,
            "notes": "Сума от PRODAGBI 02-20, без кодове 11,12,13,04."
        },
        {
            "id": 9,
            "code": "01-11",
            "internal_name": "sales_base_20",
            "name_bg": "ДО на облагаемите доставки 20%",
            "start_pos": 182,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2,
            "notes": "Сума от PRODAGBI 02-11 без кодове 11,12,13,04."
        },
        {
            "id": 10,
            "code": "01-21",
            "internal_name": "sales_vat_20",
            "name_bg": "Начислен ДДС 20%",
            "start_pos": 197,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 11,
            "code": "01-12",
            "internal_name": "sales_base_intra_community_and_82",
            "name_bg": "ДО на ВОП и ДО на получени доставки по чл.82, ал.2-6",
            "start_pos": 212,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2,
            "notes": "Сума [02-12]+[02-26] без кодове 11,12,13,04."
        },
        {
            "id": 12,
            "code": "01-22",
            "internal_name": "sales_vat_intra_community_and_82",
            "name_bg": "Начислен данък за ВОП и получени доставки по чл.82, ал.2-6",
            "start_pos": 227,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 13,
            "code": "01-23",
            "internal_name": "sales_vat_private_use",
            "name_bg": "Начислен данък за доставки за лични нужди",
            "start_pos": 242,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 14,
            "code": "01-13",
            "internal_name": "sales_base_9",
            "name_bg": "ДО на облагаеми доставки със ставка 9%",
            "start_pos": 257,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 15,
            "code": "01-24",
            "internal_name": "sales_vat_9",
            "name_bg": "Начислен ДДС 9%",
            "start_pos": 272,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 16,
            "code": "01-14",
            "internal_name": "sales_base_0_chapter3",
            "name_bg": "ДО със ставка 0% по глава трета",
            "start_pos": 287,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 17,
            "code": "01-15",
            "internal_name": "sales_base_0_intra_community_supply",
            "name_bg": "ДО със ставка 0% за ВОД",
            "start_pos": 302,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 18,
            "code": "01-16",
            "internal_name": "sales_base_0_other",
            "name_bg": "ДО със ставка 0% по чл.140, 146, 173",
            "start_pos": 317,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 19,
            "code": "01-17",
            "internal_name": "sales_base_services_21_2",
            "name_bg": "ДО на услуги по чл.21, ал.2 (други държави членки)",
            "start_pos": 332,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 20,
            "code": "01-18",
            "internal_name": "sales_base_69_2_eu",
            "name_bg": "ДО по чл.69, ал.2 (вкл. дистанционни продажби в ЕС)",
            "start_pos": 347,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 21,
            "code": "01-19",
            "internal_name": "sales_base_exempt",
            "name_bg": "ДО на освободени доставки и освободените ВОП",
            "start_pos": 362,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 22,
            "code": "01-30",
            "internal_name": "purchases_base_and_vat_no_credit",
            "name_bg": "ДО и данък на получени доставки без право на данъчен кредит или без данък",
            "start_pos": 377,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 23,
            "code": "01-31",
            "internal_name": "purchases_base_full_credit",
            "name_bg": "ДО на получени доставки с право на пълен данъчен кредит",
            "start_pos": 392,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 24,
            "code": "01-41",
            "internal_name": "purchases_vat_full_credit",
            "name_bg": "Начислен ДДС с право на пълен данъчен кредит",
            "start_pos": 407,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 25,
            "code": "01-32",
            "internal_name": "purchases_base_partial_credit",
            "name_bg": "ДО на получени доставки с право на частичен данъчен кредит",
            "start_pos": 422,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 26,
            "code": "01-42",
            "internal_name": "purchases_vat_partial_credit",
            "name_bg": "Начислен ДДС с право на частичен данъчен кредит",
            "start_pos": 437,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 27,
            "code": "01-43",
            "internal_name": "purchases_annual_correction",
            "name_bg": "Годишна корекция по чл. 73, ал. 8 ЗДДС",
            "start_pos": 452,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 28,
            "code": "01-33",
            "internal_name": "pro_rata_coefficient",
            "name_bg": "Коефициент по чл. 73, ал. 5 ЗДДС",
            "start_pos": 467,
            "width_guess": 4,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 4,
            "align": "right",
            "decimals": 2,
            "notes": "0.00 <= K <= 1.00"
        },
        {
            "id": 29,
            "code": "01-40",
            "internal_name": "total_tax_credit",
            "name_bg": "Общо данъчен кредит",
            "start_pos": 471,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2,
            "notes": "Кл.41 + кл.42 * кл.33 + кл.43"
        },
        {
            "id": 30,
            "code": "01-50",
            "internal_name": "vat_due",
            "name_bg": "ДДС за внасяне (кл.20 - кл.40) >= 0",
            "start_pos": 486,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 31,
            "code": "01-60",
            "internal_name": "vat_refundable",
            "name_bg": "ДДС за възстановяване (кл.20 - кл.40) < 0",
            "start_pos": 501,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 32,
            "code": "01-70",
            "internal_name": "vat_offset_92_1",
            "name_bg": "Данък за внасяне от кл. 50, приспаднат по чл. 92, ал. 1 ЗДДС",
            "start_pos": 516,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 33,
            "code": "01-71",
            "internal_name": "vat_paid",
            "name_bg": "Данък за внасяне от кл. 50, внесен ефективно",
            "start_pos": 531,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 34,
            "code": "01-80",
            "internal_name": "vat_refundable_92_1",
            "name_bg": "ДДС за възстановяване по чл. 92, ал. 1 ЗДДС",
            "start_pos": 546,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 35,
            "code": "01-81",
            "internal_name": "vat_refundable_92_3",
            "name_bg": "ДДС за възстановяване по чл. 92, ал. 3 ЗДДС",
            "start_pos": 561,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 36,
            "code": "01-82",
            "internal_name": "vat_refundable_92_4",
            "name_bg": "ДДС за възстановяване по чл. 92, ал. 4 ЗДДС",
            "start_pos": 576,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        }
    ]
}
""",
    "configs/schemas/pokupki-schema.json": """{
    "config_type": "pokupki",
    "config_version": 1,
    "schema_name": "pokupki_schema",
    "file_encoding": "cp1251",
    "line_length": 274,
    "newline": "CRLF",
    "fields": [
        {
            "id": 1,
            "code": "03-02",
            "internal_name": "vat_number",
            "name_bg": "Идентификационен номер по ДДС на лицето",
            "start_pos": 1,
            "width_guess": 15,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 15,
            "align": "left",
            "notes": "ИН по ДДС на регистрираното лице; задължително и трябва да съвпада с DEKLAR 00-01."
        },
        {
            "id": 2,
            "code": "03-01",
            "internal_name": "tax_period",
            "name_bg": "Данъчен период",
            "start_pos": 16,
            "width_guess": 6,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 6,
            "align": "left",
            "pattern": "YYYYMM",
            "notes": "Отчетен период, напр. 202511 за ноември 2025; трябва да съвпада с DEKLAR 00-03."
        },
        {
            "id": 3,
            "code": "03-03",
            "internal_name": "branch_number",
            "name_bg": "Клон/обособено звено",
            "start_pos": 22,
            "width_guess": 4,
            "type": "float64",
            "required": false,
            "alignment": "right",
            "length": 4,
            "align": "right",
            "decimals": 0,
            "notes": "Уникален номер на клона; 0 или празно за централно управление. Стойност от 0 до 9999."
        },
        {
            "id": 4,
            "code": "03-04",
            "internal_name": "journal_row_number",
            "name_bg": "Пореден номер на документа в дневника",
            "start_pos": 26,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "decimals": 0,
            "notes": "Нарастващ пореден номер без пропуски и дублиране за съответния данъчен период; започва от 1."
        },
        {
            "id": 5,
            "code": "03-05",
            "internal_name": "document_type",
            "name_bg": "Вид на документа",
            "start_pos": 41,
            "width_guess": 2,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 2,
            "align": "left",
            "allowed_values": [
                "01",
                "02",
                "03",
                "05",
                "07",
                "09",
                "11",
                "12",
                "13",
                "23",
                "91",
                "92",
                "93",
                "94"
            ],
            "notes": "Код за вид документ според ППЗДДС (фактура, дебитно/кредитно известие, протоколи, регистър и т.н.)."
        },
        {
            "id": 6,
            "code": "03-06",
            "internal_name": "document_number",
            "name_bg": "Номер на документа",
            "start_pos": 43,
            "width_guess": 20,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 20,
            "align": "left",
            "notes": "Съгласно общите изисквания – реалният номер на фактура/протокол и т.н. В твоя стар пример този номер е бил сложна конкатенация (брояч + вид документ + фактура); тук описваме официалното поле – НАП вижда просто текстов номер."
        },
        {
            "id": 7,
            "code": "03-07",
            "internal_name": "document_date",
            "name_bg": "Дата на документа",
            "start_pos": 63,
            "width_guess": 10,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 10,
            "align": "left",
            "pattern": "dd/MM/yyyy",
            "notes": "Дата на издаване на документа."
        },
        {
            "id": 8,
            "code": "03-08",
            "internal_name": "counterparty_vat",
            "name_bg": "Идентификационен номер на контрагента (доставчик)",
            "start_pos": 73,
            "width_guess": 15,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 15,
            "align": "left",
            "notes": "ИН на доставчика (по ЗДДС или друг идентификационен номер). За чуждестранен/физически контрагент може да е специалният код 999999999999999."
        },
        {
            "id": 9,
            "code": "03-09",
            "internal_name": "counterparty_name",
            "name_bg": "Име на контрагента (доставчик)",
            "start_pos": 88,
            "width_guess": 50,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 50,
            "align": "left",
            "notes": "Наименование на доставчика; задължително ако е попълнен ИН на контрагента."
        },
        {
            "id": 10,
            "code": "03-10",
            "internal_name": "goods_or_service_description",
            "name_bg": "Вид на стоката или обхват и вид на услугата",
            "start_pos": 138,
            "width_guess": 30,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 30,
            "align": "left",
            "notes": "Кратко описание на стоката/услугата по документа."
        },
        {
            "id": 11,
            "code": "03-30",
            "internal_name": "base_and_vat_no_credit",
            "name_bg": "Данъчна основа и данък на получените доставки без право на данъчен кредит или без данък",
            "start_pos": 168,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2,
            "notes": "Поле описващо стойност; включва доставки/ВОП/чл.82/внос без право на данъчен кредит или без данък."
        },
        {
            "id": 12,
            "code": "03-31",
            "internal_name": "base_full_credit",
            "name_bg": "ДО с право на пълен данъчен кредит",
            "start_pos": 183,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 13,
            "code": "03-41",
            "internal_name": "vat_full_credit",
            "name_bg": "ДДС с право на пълен данъчен кредит",
            "start_pos": 198,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 14,
            "code": "03-32",
            "internal_name": "base_partial_credit",
            "name_bg": "ДО с право на частичен данъчен кредит",
            "start_pos": 213,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 15,
            "code": "03-42",
            "internal_name": "vat_partial_credit",
            "name_bg": "ДДС с право на частичен данъчен кредит",
            "start_pos": 228,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 16,
            "code": "03-43",
            "internal_name": "annual_correction",
            "name_bg": "Годишна корекция по чл. 73, ал. 8 ЗДДС",
            "start_pos": 243,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 17,
            "code": "03-44",
            "internal_name": "base_triangular",
            "name_bg": "ДО при придобиване на стоки от посредник в тристранна операция",
            "start_pos": 258,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 18,
            "code": "03-45",
            "internal_name": "special_supply_code",
            "name_bg": "Доставка по чл. 163а или внос по чл. 167а от ЗДДС",
            "start_pos": 273,
            "width_guess": 2,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 2,
            "align": "left",
            "allowed_values": [
                "01",
                "02",
                "03",
                "07",
                "08",
                "51",
                "53",
                "54",
                "58"
            ],
            "notes": "Код за доставки по чл.163а/внос по чл.167а и операции по режим складиране на стоки до поискване."
        }
    ]
}
""",
    "configs/schemas/prodagbi-schema.json": """{
    "config_type": "prodagbi",
    "config_version": 1,
    "schema_name": "prodagbi_schema",
    "file_encoding": "cp1251",
    "line_length": 424,
    "newline": "CRLF",
    "fields": [
        {
            "id": 1,
            "code": "02-00",
            "internal_name": "vat_number",
            "name_bg": "Идентификационен номер по ДДС на лицето",
            "start_pos": 1,
            "width_guess": 15,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 15,
            "align": "left",
            "notes": "ИН по ДДС на регистрираното лице; трябва да съвпада с DEKLAR 00-01."
        },
        {
            "id": 2,
            "code": "02-01",
            "internal_name": "tax_period",
            "name_bg": "Данъчен период",
            "start_pos": 16,
            "width_guess": 6,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 6,
            "align": "left",
            "pattern": "YYYYMM",
            "notes": "Отчетен период, напр. 202511."
        },
        {
            "id": 3,
            "code": "02-02",
            "internal_name": "branch_number",
            "name_bg": "Клон/обособено звено",
            "start_pos": 22,
            "width_guess": 4,
            "type": "float64",
            "required": false,
            "alignment": "right",
            "length": 4,
            "align": "right",
            "decimals": 0,
            "notes": "0 или празно за централно управление; иначе 1–9999."
        },
        {
            "id": 4,
            "code": "02-03",
            "internal_name": "journal_row_number",
            "name_bg": "Пореден номер на документа в дневника",
            "start_pos": 26,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "decimals": 0,
            "notes": "Нарастващ пореден номер; започва от 1, без пропуски; последният съвпада с броя документи по DEKLAR 00-05."
        },
        {
            "id": 5,
            "code": "02-04",
            "internal_name": "document_type",
            "name_bg": "Вид на документа",
            "start_pos": 41,
            "width_guess": 2,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 2,
            "align": "left",
            "allowed_values": [
                "01",
                "02",
                "03",
                "04",
                "07",
                "09",
                "11",
                "12",
                "13",
                "23",
                "29",
                "50",
                "81",
                "82",
                "83",
                "84",
                "85",
                "91",
                "93",
                "94",
                "95"
            ],
            "notes": "Код за вид документ; за PRODAGBI не се допуска 05 и 92. Част от кодовете (11,12,13) за касова отчетност."
        },
        {
            "id": 6,
            "code": "02-05",
            "internal_name": "document_number",
            "name_bg": "Номер на документа",
            "start_pos": 43,
            "width_guess": 20,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 20,
            "align": "left",
            "notes": "Реален номер на фактура/протокол и т.н. В твоя стар пример този номер често е бил конструиран (брояч + вид документ + фактура); в официалния формат това си е просто 'номер на документ'."
        },
        {
            "id": 7,
            "code": "02-06",
            "internal_name": "document_date",
            "name_bg": "Дата на документа",
            "start_pos": 63,
            "width_guess": 10,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 10,
            "align": "left",
            "pattern": "dd/MM/yyyy",
            "notes": "Дата на издаване на документа; задължителна според общите изисквания."
        },
        {
            "id": 8,
            "code": "02-07",
            "internal_name": "counterparty_vat",
            "name_bg": "Идентификационен номер на контрагента (получател)",
            "start_pos": 73,
            "width_guess": 15,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 15,
            "align": "left",
            "notes": "ИН на получателя – по ЗДДС или по §1 ППЗДДС; може да бъде 999999999999999 за определени случаи."
        },
        {
            "id": 9,
            "code": "02-08",
            "internal_name": "counterparty_name",
            "name_bg": "Име на контрагента (получател)",
            "start_pos": 88,
            "width_guess": 50,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 50,
            "align": "left"
        },
        {
            "id": 10,
            "code": "02-09",
            "internal_name": "goods_or_service_description",
            "name_bg": "Вид на стоката или обхват и вид на услугата",
            "start_pos": 138,
            "width_guess": 30,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 30,
            "align": "left",
            "notes": "Точно описание по документа."
        },
        {
            "id": 11,
            "code": "02-10",
            "internal_name": "total_tax_base",
            "name_bg": "Общ размер на данъчните основи за облагане с ДДС",
            "start_pos": 168,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2,
            "notes": "Сума от 02-11, 02-12, 02-13, 02-14, 02-15, 02-16, 02-26."
        },
        {
            "id": 12,
            "code": "02-20",
            "internal_name": "total_vat",
            "name_bg": "Всичко начислен ДДС",
            "start_pos": 183,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2,
            "notes": "Сума от 02-21, 02-22, 02-23, 02-24."
        },
        {
            "id": 13,
            "code": "02-11",
            "internal_name": "base_20",
            "name_bg": "ДО на облагаемите доставки със ставка 20%",
            "start_pos": 198,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 14,
            "code": "02-21",
            "internal_name": "vat_20",
            "name_bg": "Начислен ДДС 20%",
            "start_pos": 213,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 15,
            "code": "02-12",
            "internal_name": "base_intra_community_acq",
            "name_bg": "ДО на ВОП",
            "start_pos": 228,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 16,
            "code": "02-26",
            "internal_name": "base_reverse_charge_82",
            "name_bg": "ДО по получените доставки по чл. 82, ал. 2 - 5 ЗДДС",
            "start_pos": 243,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 17,
            "code": "02-22",
            "internal_name": "vat_intra_community_and_82",
            "name_bg": "Начислен ДДС за ВОП и за получени доставки по чл. 82, ал. 2 - 5 ЗДДС",
            "start_pos": 258,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 18,
            "code": "02-23",
            "internal_name": "vat_for_private_use",
            "name_bg": "Начислен данък за доставки за лични нужди",
            "start_pos": 273,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 19,
            "code": "02-13",
            "internal_name": "base_9",
            "name_bg": "ДО на облагаемите доставки със ставка 9%",
            "start_pos": 288,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 20,
            "code": "02-24",
            "internal_name": "vat_9",
            "name_bg": "Начислен ДДС 9%",
            "start_pos": 303,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 21,
            "code": "02-14",
            "internal_name": "base_0_chapter3",
            "name_bg": "ДО на доставките със ставка 0% по глава трета",
            "start_pos": 318,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 22,
            "code": "02-15",
            "internal_name": "base_0_intra_community_supply",
            "name_bg": "ДО на доставките със ставка 0% на ВОД на стоки",
            "start_pos": 333,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 23,
            "code": "02-16",
            "internal_name": "base_0_other",
            "name_bg": "ДО на доставките със ставка 0% по чл. 140, чл. 146, ал. 1 и чл. 173 ЗДДС",
            "start_pos": 348,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 24,
            "code": "02-17",
            "internal_name": "base_services_21_2",
            "name_bg": "ДО на доставки на услуги по чл. 21, ал. 2 ЗДДС",
            "start_pos": 363,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 25,
            "code": "02-18",
            "internal_name": "base_69_2_eu",
            "name_bg": "ДО по чл. 69, ал. 2 ЗДДС (дистанционни продажби, други държави членки)",
            "start_pos": 378,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 26,
            "code": "02-19",
            "internal_name": "base_exempt",
            "name_bg": "ДО на освободени доставки и освободените ВОП",
            "start_pos": 393,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 27,
            "code": "02-25",
            "internal_name": "base_triangular",
            "name_bg": "ДО на доставки като посредник в тристранни операции",
            "start_pos": 408,
            "width_guess": 15,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 15,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 28,
            "code": "02-27",
            "internal_name": "special_supply_code",
            "name_bg": "Доставка по чл. 163а или внос по чл. 167а от ЗДДС",
            "start_pos": 423,
            "width_guess": 2,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 2,
            "align": "left",
            "allowed_values": [
                "01",
                "02",
                "03",
                "07",
                "08",
                "41",
                "43",
                "46",
                "48"
            ],
            "notes": "Код за чл.163а/167а и операции по режим складиране на стоки до поискване."
        }
    ]
}
""",
    "configs/schemas/vies-schema.json": """{
    "config_type": "vies",
    "config_version": 1,
    "schema_name": "vies_schema",
    "file_encoding": "cp1251",
    "line_length": 373,
    "newline": "CRLF",
    "description": "Schema definition for the Bulgarian VIES.TXT file used when submitting VIES declarations.  Each section of the file has fixed‑width fields.  This schema describes the field order, lengths and data types for the standard sections: main record (VHR), declarer (VDR), registered person (VTR), total turnover (TTR) and intra‑community deliveries (VIR).  Optional call‑off stock sections (CHR/COS) are not included.",
    "fields": [
        {
            "id": 1,
            "code": "VHR-01",
            "internal_name": "vhr_section_code",
            "name_bg": "Код на секцията \"Основен запис\"",
            "start_pos": 1,
            "width_guess": 3,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 3,
            "align": "left",
            "notes": "Constant value 'VHR'"
        },
        {
            "id": 2,
            "code": "VHR-02",
            "internal_name": "reporting_period",
            "name_bg": "Отчетен период",
            "start_pos": 4,
            "width_guess": 7,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 7,
            "align": "left",
            "pattern": "MM/YYYY"
        },
        {
            "id": 3,
            "code": "VHR-03",
            "internal_name": "total_record_count",
            "name_bg": "Общ брой редове в декларацията",
            "start_pos": 11,
            "width_guess": 5,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 5,
            "align": "right",
            "decimals": 0
        },
        {
            "id": 4,
            "code": "VDR-01",
            "internal_name": "vdr_section_code",
            "name_bg": "Код на секцията \"Декларатор\"",
            "start_pos": 1,
            "width_guess": 3,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 3,
            "align": "left",
            "notes": "Constant value 'VDR'"
        },
        {
            "id": 5,
            "code": "VDR-02",
            "internal_name": "declarer_id",
            "name_bg": "ЕГН/ЛНЧ на лицето, подаващо декларацията",
            "start_pos": 4,
            "width_guess": 15,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 15,
            "align": "left"
        },
        {
            "id": 6,
            "code": "VDR-03",
            "internal_name": "declarer_name",
            "name_bg": "Трите имена по лична карта на лицето, подаващо декларацията",
            "start_pos": 19,
            "width_guess": 150,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 150,
            "align": "left"
        },
        {
            "id": 7,
            "code": "VDR-04",
            "internal_name": "declarer_city",
            "name_bg": "Град от адреса за кореспонденция на лицето, подаващо декларацията",
            "start_pos": 169,
            "width_guess": 50,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 50,
            "align": "left"
        },
        {
            "id": 8,
            "code": "VDR-05",
            "internal_name": "declarer_postal_code",
            "name_bg": "Пощенски код от адреса за кореспонденция на лицето, подаващо декларацията",
            "start_pos": 219,
            "width_guess": 4,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 4,
            "align": "right",
            "decimals": 0
        },
        {
            "id": 9,
            "code": "VDR-06",
            "internal_name": "declarer_address",
            "name_bg": "Адрес за кореспонденция (кв., ж.к., ул., №) на лицето, подаващо декларацията",
            "start_pos": 223,
            "width_guess": 150,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 150,
            "align": "left"
        },
        {
            "id": 10,
            "code": "VDR-07",
            "internal_name": "declarer_person_type",
            "name_bg": "Качество на лицето, подаващо декларацията (A – пълномощник, R – представляващ)",
            "start_pos": 373,
            "width_guess": 1,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 1,
            "align": "left"
        },
        {
            "id": 11,
            "code": "VTR-01",
            "internal_name": "vtr_section_code",
            "name_bg": "Код на секцията \"Регистрирано лице\"",
            "start_pos": 1,
            "width_guess": 3,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 3,
            "align": "left",
            "notes": "Constant value 'VTR'"
        },
        {
            "id": 12,
            "code": "VTR-02",
            "internal_name": "registered_vat_number",
            "name_bg": "Идентификационен номер по ДДС на регистрираното лице",
            "start_pos": 4,
            "width_guess": 15,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 15,
            "align": "left"
        },
        {
            "id": 13,
            "code": "VTR-03",
            "internal_name": "registered_name",
            "name_bg": "Име на регистрираното лице",
            "start_pos": 19,
            "width_guess": 150,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 150,
            "align": "left"
        },
        {
            "id": 14,
            "code": "VTR-04",
            "internal_name": "registered_address",
            "name_bg": "Адрес за кореспонденция на регистрираното лице",
            "start_pos": 169,
            "width_guess": 200,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 200,
            "align": "left"
        },
        {
            "id": 15,
            "code": "TTR-01",
            "internal_name": "ttr_section_code",
            "name_bg": "Код на секцията \"Общ оборот\"",
            "start_pos": 1,
            "width_guess": 3,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 3,
            "align": "left",
            "notes": "Constant value 'TTR'"
        },
        {
            "id": 16,
            "code": "TTR-02",
            "internal_name": "total_tax_base",
            "name_bg": "Данъчна основа общо (сума по к3 + к4 + к5)",
            "start_pos": 4,
            "width_guess": 12,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 12,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 17,
            "code": "TTR-03",
            "internal_name": "vod_tax_base",
            "name_bg": "Данъчна основа на ВОД (сума по к3)",
            "start_pos": 16,
            "width_guess": 12,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 12,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 18,
            "code": "VIR-01",
            "internal_name": "vir_section_code",
            "name_bg": "Код на секцията \"ВОД\"",
            "start_pos": 1,
            "width_guess": 3,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 3,
            "align": "left",
            "notes": "Constant value 'VIR'"
        },
        {
            "id": 19,
            "code": "VIR-02",
            "internal_name": "line_number",
            "name_bg": "Номер на ред",
            "start_pos": 4,
            "width_guess": 5,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 5,
            "align": "right",
            "decimals": 0
        },
        {
            "id": 20,
            "code": "VIR-03",
            "internal_name": "counterparty_vat",
            "name_bg": "VIN номер на чуждестранния контрагент (идентификационен номер по ДДС, включително префикса на държавата)",
            "start_pos": 9,
            "width_guess": 15,
            "type": "object",
            "required": true,
            "alignment": "left",
            "length": 15,
            "align": "left"
        },
        {
            "id": 21,
            "code": "VIR-04",
            "internal_name": "goods_tax_base",
            "name_bg": "Обща стойност на данъчната основа за доставки на стоки",
            "start_pos": 24,
            "width_guess": 12,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 12,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 22,
            "code": "VIR-05",
            "internal_name": "triangular_tax_base",
            "name_bg": "Обща стойност на данъчната основа за тристранни сделки",
            "start_pos": 36,
            "width_guess": 12,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 12,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 23,
            "code": "VIR-06",
            "internal_name": "services_tax_base",
            "name_bg": "Обща стойност на данъчната основа за доставени услуги по чл. 21, ал. 2 от ЗДДС",
            "start_pos": 48,
            "width_guess": 12,
            "type": "float64",
            "required": true,
            "alignment": "right",
            "length": 12,
            "align": "right",
            "is_amount": true,
            "decimals": 2
        },
        {
            "id": 24,
            "code": "VIR-07",
            "internal_name": "vir_reporting_period",
            "name_bg": "Отчетен период за реда (попълва се само ако се различава от отчетния период на основния запис)",
            "start_pos": 60,
            "width_guess": 7,
            "type": "object",
            "required": false,
            "alignment": "left",
            "length": 7,
            "align": "left",
            "pattern": "MM/YYYY"
        }
    ]
}
""",
}


def restore_default_configs(base_dir: str) -> None:
    for rel_path, content in DEFAULT_CONFIG_CONTENTS.items():
        target = Path(base_dir) / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content + "\n", encoding="utf-8")
