

def main():

    question = 'What does the third semester of a Agribusiness Management major look like?'
    answer = """The third semester of an Agribusiness Management major includes the following courses:

        - **ACCT 102 Foundations of Managerial Accounting** - 3 credits
        - **ECON 103 Microeconomics** - 3 credits
        - **BSAD 203 Marketing** - 3 credits
        - **BSAD 215 Small Business Management** - 3 credits
        - **Other World Civilization (GER 6)** - 3 credits

        Total Credits: 15"""

    qa = [
        ("What percentage of Buffalo State's enrollment was undergraduate in Fall 2013?", "84.3%"),
        ("What percentage of Buffalo State's enrollment was undergraduate in Fall 2018?", "88.6%"),
        ("What percentage of Suny POLY's enrollment was undergraduate in Fall 2016?", "74.3%"),
        ("What percentage of Suny Niagara County's enrollment was undergraduate in Fall 2023?", "100.0%"),
        ("What percentage of SUNY Potsdam's enrollment was undergraduate in Fall 2018?", "93.7%"),
    ]

    pdf_text = pdf_to_text(pdf_file)[0]
    llama_text = load_pdf_text_with_llama(pdf_file)
    gpt_pdf_text = parse_pdf_with_gpt(pdf_file, [])

    for q, a in qa:
        question = '**Question:** ' + q + '\n\n'
        question1 = question + '**Reference Data:**\n\n' + llama_text
        question2 = question + '**Reference Data:**\n\n' + pdf_text
        question3 = question + '**Reference Data:**\n\n' + gpt_pdf_text

        print('question:', q)
        print('answer:', a)

        suny_agent.add_message("user", question1)
        response = suny_agent.invoke()
        print('Llama answer:')
        print(response.choices[0].message.content)
        suny_agent.delete_last_message()

        suny_agent.add_message("user", question2)
        response = suny_agent.invoke()
        print('PDF answer:')
        print(response.choices[0].message.content)
        suny_agent.delete_last_message()

        suny_agent.add_message("user", question3)
        response = suny_agent.invoke()
        print('GPT answer:')
        print(response.choices[0].message.content, '\n----------------\n')
        suny_agent.delete_last_message()


if __name__ == "__main__":
    main()
